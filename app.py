"""Private server studio: durable jobs, local voices, editable cues and CPU animation."""
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import re
import ipaddress
import shutil
import signal
import sys
import sqlite3
import subprocess
import threading
import time
import uuid
import wave
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from renderer import frame

ROOT=Path(__file__).parent
DATA=Path(os.environ.get('STUDIO_DATA',str(ROOT/'data')))
DATA.mkdir(parents=True,exist_ok=True)
JOBS=DATA/'jobs';JOBS.mkdir(exist_ok=True)
DB=DATA/'studio.sqlite'
VS=os.environ.get('VOICESTUDIO_URL','http://127.0.0.1:3900')
MODELS=Path(os.environ.get('STUDIO_MODELS_DIR',str(ROOT/'models')))
RHUBARB=Path(os.environ.get('RHUBARB_PATH',shutil.which('rhubarb') or str(ROOT/'tools/rhubarb/rhubarb')))
LOCAL_NETWORKS=[ipaddress.ip_network(value.strip()) for value in os.environ.get('STUDIO_ALLOWED_NETWORKS','127.0.0.0/8,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16').split(',') if value.strip()]
LOCAL_HOSTS={'localhost','127.0.0.1','::1',*(value.strip() for value in os.environ.get('STUDIO_ALLOWED_HOSTS','').split(',') if value.strip())}
STOP=threading.Event()
CURRENT={}
VOICES={
    'local-northern':{'label':'Northern English · male','engine':'piper','model':'northern','description':'Local neural speech · CC BY-SA dataset; see notices'},
    'local-cori':{'label':'Cori · British female','engine':'piper','model':'cori','description':'Local neural speech · female'},
    'studio-female':{'label':'VoiceStudio · female preset','engine':'voicestudio','backend':'kittentts','preset_voice':'expr-voice-2-f'},
    'studio-male':{'label':'VoiceStudio · male preset','engine':'voicestudio','backend':'kittentts','preset_voice':'expr-voice-2-m'},
}

@contextlib.contextmanager
def db():
    c=sqlite3.connect(DB,timeout=15);c.row_factory=sqlite3.Row
    try:
        c.execute('PRAGMA journal_mode=WAL')
        with c:yield c
    finally:c.close()

def init_db():
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, spec TEXT, status TEXT, stage TEXT, progress REAL DEFAULT 0, error TEXT, created REAL, updated REAL, cancel INTEGER DEFAULT 0)')
        c.execute("UPDATE jobs SET status='queued',stage='Resuming after restart',progress=0 WHERE status='running'")
        c.execute("UPDATE jobs SET status='cancelled',stage='Cancelled' WHERE cancel=1 AND status='queued'")

def update(jid,**fields):
    fields['updated']=time.time()
    with db() as c:c.execute('UPDATE jobs SET '+','.join(k+'=?' for k in fields)+' WHERE id=?',list(fields.values())+[jid])

def cancelled(jid):
    with db() as c:r=c.execute('SELECT cancel FROM jobs WHERE id=?',(jid,)).fetchone()
    return STOP.is_set() or not r or bool(r['cancel'])

class Cancelled(Exception):pass

def check(jid):
    if cancelled(jid):raise Cancelled()

def run(cmd,jid,timeout=180):
    check(jid)
    with subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True) as p:
        CURRENT[jid]=p
        start=time.monotonic()
        try:
            while True:
                try:out,err=p.communicate(timeout=.4);break
                except subprocess.TimeoutExpired:
                    check(jid)
                    if time.monotonic()-start>timeout:raise TimeoutError('Local engine timed out')
            check(jid)
            if p.returncode:raise RuntimeError(err.decode(errors='replace')[-1800:] or 'Local engine failed')
            return out
        finally:
            CURRENT.pop(jid,None)
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()

def atomic_json(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(path)

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def wav_seconds(path):
    with wave.open(str(path)) as f:return f.getnframes()/f.getframerate()

def synthesize(jid,spec,dest):
    voice=VOICES[spec['voice']]
    if voice['engine']=='piper':
        model=MODELS/f"{voice['model']}.onnx"
        if not model.exists():raise RuntimeError('This local voice model is not installed')
        # Piper CLI accepts input text via a file, never through a shell.
        textfile=dest.parent/'script.txt';textfile.write_text(spec['text'].replace('\n',' '))
        run([sys.executable,'-m','piper','-m',str(model),'-f',str(dest),
             '--length-scale',str(1/spec['speed']),'--input-file',str(textfile)],jid,180)
    else:
        keypath=Path(os.environ.get('VOICESTUDIO_API_KEY_FILE',str(ROOT/'private/voicestudio-key')))
        if not keypath.exists():raise RuntimeError('VoiceStudio is not configured; select an installed local voice')
        headers={'Authorization':'Bearer '+keypath.read_text().strip()}
        # This address is fixed in server configuration, never supplied by the browser.
        payload={'text':spec['text'],'language':'English','engine':voice['backend'],'preset_voice':voice['preset_voice'],
                 'seed':'42','num_step':'16','speed':str(spec['speed']),'effect_preset':'raw','denoise':'false','postprocess_output':'false'}
        with httpx.Client(timeout=1800,trust_env=False) as client:
            # systemd can start the UI before the backend has registered routes.
            # Wait for this exact local engine, without submitting duplicate speech.
            ready=False
            for _ in range(90):
                check(jid)
                try:
                    health=client.get(VS+'/engines/'+voice['backend']+'/health',headers=headers,timeout=2)
                    if health.status_code==401:raise RuntimeError('Local speech authentication failed')
                    if health.is_success:ready=True;break
                except httpx.TransportError:pass
                STOP.wait(1)
            if not ready:raise RuntimeError('Local speech service did not become ready; resume this scene after checking the voice service')
            res=client.post(VS+'/generate',data=payload,headers=headers)
            if not res.is_success:raise RuntimeError(f'VoiceStudio rejected speech ({res.status_code}): '+res.text[:500])
            if res.headers.get('X-OmniVoice-Dropped-Chunks','0')!='0':raise RuntimeError('VoiceStudio dropped part of the script; output rejected')
            if 'json' in res.headers.get('content-type',''):
                result=res.json()
                audio=result.get('audio_url') or result.get('url')
                if not audio:raise RuntimeError('VoiceStudio returned no audio URL')
                # Never follow a provider URL from an engine response.
                if not audio.startswith('/') or audio.startswith('//'):raise RuntimeError('VoiceStudio returned a non-local audio URL')
                check(jid)
                res=client.get(VS+audio,headers=headers);res.raise_for_status()
            dest.write_bytes(res.content)
    if not dest.exists() or dest.stat().st_size<1000:raise RuntimeError('Speech output is empty')
    seconds=wav_seconds(dest)
    if seconds<=.1 or seconds>180:raise RuntimeError('Speech duration is outside the supported 0–180 second range')
    return seconds

def caption_cues(text,cues,duration):
    # Transcript display timing is approximate; mouth timing comes from Rhubarb.
    chunks=re.findall(r'[^.!?]+[.!?]?',text)
    chunks=[v.strip() for v in chunks if v.strip()]
    total=sum(len(v.split()) for v in chunks) or 1
    start=0;result=[]
    for v in chunks:
        end=min(duration,start+duration*len(v.split())/total)
        result.append({'start':round(start,3),'end':round(end,3),'text':v});start=end
    return result

def make_srt(captions):
    def ts(t):
        ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
    return '\n\n'.join(f"{i+1}\n{ts(c['start'])} --> {ts(c['end'])}\n{c['text']}" for i,c in enumerate(captions))+'\n'

def pipeline(jid,spec):
    folder=JOBS/jid;folder.mkdir(exist_ok=True)
    start=time.monotonic(); timings={}
    if shutil.disk_usage(DATA).free<2*1024**3:raise RuntimeError('Less than 2GB free server disk space')
    voice=folder/'speech.wav'
    update(jid,stage='Generating local speech',progress=.03)
    if voice.exists():duration=wav_seconds(voice)
    else:
        partial=folder/'speech.partial.wav'
        duration=synthesize(jid,spec,partial)
        check(jid);partial.replace(voice)
    timings['speech']=round(time.monotonic()-start,3)
    check(jid)
    cuesfile=folder/'mouth-cues.json'
    update(jid,stage='Aligning speech to mouth poses',progress=.18)
    if not cuesfile.exists():
        transcript=folder/'script.txt';transcript.write_text(spec['text'])
        cuepart=folder/'mouth-cues.partial.json'
        run([str(RHUBARB),'--threads','2','-f','json','-o',str(cuepart),'-d',str(transcript),str(voice)],jid,360)
        json.loads(cuepart.read_text())['mouthCues']
        cuepart.replace(cuesfile)
    cues=json.loads(cuesfile.read_text())['mouthCues']
    edits=folder/'cue-edits.json'
    if edits.exists():cues=json.loads(edits.read_text())
    timings['alignment']=round(time.monotonic()-start-timings['speech'],3)
    captions=caption_cues(spec['text'],cues,duration)
    spec={**spec,'captions':captions}
    (folder/'captions.srt').write_text(make_srt(captions))
    atomic_json(folder/'render-spec.json',spec)
    renderstart=time.monotonic()
    fps=24; length=duration+.35; count=math.ceil(length*fps)
    out=folder/'render.partial.mp4'; final=folder/'video.mp4'
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f"{spec['width']}x{spec['height']}",'-framerate',str(fps),'-i','pipe:0','-i',str(voice),'-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-af','apad','-t',str(length),'-movflags','+faststart',str(out)]
    update(jid,stage='Animating and encoding on server',progress=.25)
    with open(folder/'encoder.log','wb') as log, subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log,start_new_session=True) as p:
        CURRENT[jid]=p
        try:
            for i in range(count):
                check(jid)
                image=frame(i/fps,length,cues,spec)
                if i==min(24,count-1):image.save(folder/'poster.webp','WEBP',quality=92)
                p.stdin.write(image.tobytes())
                if i%24==0:update(jid,progress=.25+.66*i/count)
            p.stdin.close();p.stdin=None
            p.wait(timeout=120)
            if p.returncode:raise RuntimeError('Encoder failed: '+(folder/'encoder.log').read_text()[-1000:])
        finally:
            CURRENT.pop(jid,None)
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    timings['render']=round(time.monotonic()-renderstart,3)
    check(jid)
    update(jid,stage='Checking complete export',progress=.94)
    run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'],jid,180)
    probe=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(out)],jid))
    out.replace(final)
    atomic_json(folder/'evidence.json',{'job':jid,'created':time.time(),'runtime':'Self-hosted CPU worker','engine':VOICES[spec['voice']]['engine'],'voice':spec['voice'],'fresh_audio':'parent_job' not in spec,'parent_job':spec.get('parent_job'),'fresh_animation':True,'speech_sha256':digest(voice),'video_sha256':digest(final),'duration':duration,'cues':len(cues),'frames':count,'fps':fps,'timings':timings,'total_seconds':round(time.monotonic()-start,3),'full_decode':True,'external_inference':False,'captions':'Approximate sentence timing from transcript; editable SRT','performance_approval':'Pending playback review','probe':probe})
    update(jid,status='complete',stage='Ready for playback review',progress=1,error=None)

def worker():
    while not STOP.is_set():
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute("SELECT * FROM jobs WHERE status='queued' AND cancel=0 ORDER BY created LIMIT 1").fetchone()
            if row:c.execute("UPDATE jobs SET status='running',stage='Starting',updated=? WHERE id=?",(time.time(),row['id']))
        if not row:STOP.wait(.5);continue
        jid=row['id']
        try:pipeline(jid,json.loads(row['spec']))
        except Cancelled:
            if STOP.is_set():update(jid,status='queued',stage='Waiting to resume')
            else:update(jid,status='cancelled',stage='Cancelled',error=None)
        except Exception as exc:
            if STOP.is_set():update(jid,status='queued',stage='Waiting to resume',error=None)
            elif cancelled(jid):update(jid,status='cancelled',stage='Cancelled',error=None)
            else:update(jid,status='failed',stage='Needs attention',error=str(exc)[:2000])

@asynccontextmanager
async def lifespan(app):
    STOP.clear();init_db();t=threading.Thread(target=worker,daemon=True);t.start()
    yield
    STOP.set()
    for p in list(CURRENT.values()):
        with contextlib.suppress(ProcessLookupError):os.killpg(p.pid,signal.SIGTERM)
    t.join(timeout=5)

app=FastAPI(title='Cali Local Studio',lifespan=lifespan)

@app.middleware('http')
async def private_access(request:Request,call_next):
    # Trusted local networks only: no user-facing login or access key.
    # Restrict the actual peer and Host, rather than trusting forwarded headers.
    try:
        peer=ipaddress.ip_address(request.client.host)
        local_peer=any(peer in network for network in LOCAL_NETWORKS)
    except (ValueError,AttributeError):local_peer=False
    host=request.url.hostname or ''
    local_host=host in LOCAL_HOSTS
    if not local_host:
        try:local_host=any(ipaddress.ip_address(host) in network for network in LOCAL_NETWORKS)
        except ValueError:pass
    if not local_peer or not local_host:
        return JSONResponse({'detail':'Studio is available only on the local network'},status_code=403)
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin=request.headers.get('origin')
        if origin and origin!=str(request.base_url).rstrip('/'):
            return JSONResponse({'detail':'Cross-origin request rejected'},status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    return response

@app.get('/health')
def health():return {'ok':True,'service':'local-video-studio','paid_providers':False}

@app.get('/api/system')
def system():
    free=shutil.disk_usage(DATA).free
    voices=[]
    for key,v in VOICES.items():
        if v.get('retired'):continue
        ready=(MODELS/f"{v.get('model','')}.onnx").exists() if v['engine']=='piper' else (DATA/'voicestudio-ready.json').exists()
        voices.append({'id':key,**v,'installed':ready})
    return {'voices':voices,'renderer':'Articulated 2D characters · CPU','host':'Self-hosted studio','disk_free_gb':round(free/1024**3,1),'external_inference':False,'rhubarb':RHUBARB.is_file(),'quality_status':'Review generated speech and mouth timing before publishing.'}

class Spec(BaseModel):
    title:str=Field(default='Untitled scene',min_length=1,max_length=100)
    text:str=Field(min_length=2,max_length=1800)
    character:str='human'
    voice:str='local-cori'
    format:str='portrait'
    resolution:str='preview'
    speed:float=Field(default=1,ge=.7,le=1.3)
    motion:float=Field(default=.65,ge=0,le=1)
    mouth:float=Field(default=.75,ge=.2,le=1.2)
    sync_offset:float=Field(default=0,ge=-.5,le=.5)

def validated(body):
    spec=body.model_dump()
    spec['text']=spec['text'].strip()
    spec['title']=spec['title'].strip()
    if len(spec['text'])<2 or not spec['title']:raise HTTPException(422,'Enter a scene name and some spoken text')
    if body.character not in ['human','canine'] or body.voice not in VOICES:raise HTTPException(422,'Unknown character or voice')
    if VOICES[body.voice].get('retired'):raise HTTPException(422,'This historical test voice has been retired; choose another voice')
    if body.format not in ['portrait','landscape'] or body.resolution not in ['preview','hd']:raise HTTPException(422,'Unknown export format')
    if VOICES[body.voice]['engine']=='voicestudio' and not (DATA/'voicestudio-ready.json').exists():raise HTTPException(409,'VoiceStudio is not ready; its speech test must pass first')
    wh=(540,960) if body.resolution=='preview' else (1080,1920)
    if body.format=='landscape':wh=wh[::-1]
    spec.update(width=wh[0],height=wh[1]);return spec

def jobrow(r):
    result=dict(r);result['spec']=json.loads(result['spec'])
    result['video_url']=f"/media/{r['id']}/video.mp4" if r['status']=='complete' else None
    return result

@app.get('/api/jobs')
def jobs():
    with db() as c:return [jobrow(r) for r in c.execute('SELECT * FROM jobs ORDER BY created DESC LIMIT 100')]

@app.get('/api/jobs/{jid}')
def job(jid:str):
    with db() as c:r=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
    if not r:raise HTTPException(404,'Job not found')
    return jobrow(r)

@app.post('/api/jobs')
def create(body:Spec):
    spec=validated(body);jid=uuid.uuid4().hex[:16]
    with db() as c:
        count=c.execute("SELECT count(*) FROM jobs WHERE status IN ('running','queued')").fetchone()[0]
        if count>=8:raise HTTPException(429,'The queue is full; wait for a scene to finish')
        c.execute('INSERT INTO jobs(id,spec,status,stage,created,updated) VALUES(?,?,?,?,?,?)',(jid,json.dumps(spec),'queued','Queued',time.time(),time.time()))
    return {'id':jid}

@app.post('/api/jobs/{jid}/cancel')
def cancel(jid:str):
    r=job(jid)
    if r['status'] not in ['queued','running']:raise HTTPException(409,'Job is not active')
    update(jid,cancel=1,status='cancelled' if r['status']=='queued' else 'running',stage='Cancelling');return {'ok':True}

@app.post('/api/jobs/{jid}/retry')
def retry(jid:str):
    r=job(jid)
    if r['status'] not in ['failed','cancelled']:raise HTTPException(409,'Only failed or cancelled jobs can resume')
    update(jid,cancel=0,status='queued',stage='Queued to resume',error=None);return {'ok':True}

class Cue(BaseModel):
    start:float=Field(ge=0,le=180)
    end:float=Field(gt=0,le=181)
    value:str

class CueEdit(BaseModel):
    cues:list[Cue]=Field(min_length=1,max_length=3000)

@app.get('/api/jobs/{jid}/cues')
def getcues(jid:str):
    job(jid);p=JOBS/jid/'cue-edits.json'
    if p.exists():return json.loads(p.read_text())
    p=JOBS/jid/'mouth-cues.json'
    if not p.exists():return []
    return json.loads(p.read_text())['mouthCues']

@app.post('/api/jobs/{jid}/cues')
def editcues(jid:str,body:CueEdit):
    r=job(jid)
    if r['status'] not in ['complete','failed','cancelled']:raise HTTPException(409,'Wait for the render to finish')
    prev=0
    for cue in body.cues:
        if cue.value not in 'ABCDEFGHX' or len(cue.value)!=1 or cue.start<prev or cue.end<=cue.start:raise HTTPException(422,'Mouth cues must be ordered, non-overlapping and use A–H or X')
        prev=cue.end
    # Preserve the approved/rendered original; create a new render revision.
    spec=r['spec'];new=uuid.uuid4().hex[:16];folder=JOBS/new;folder.mkdir()
    for name in ['speech.wav','script.txt','mouth-cues.json']:
        src=JOBS/jid/name
        if src.exists():shutil.copy2(src,folder/name)
    atomic_json(folder/'cue-edits.json',[c.model_dump() for c in body.cues])
    spec['title']=spec['title'][:85]+' · revised'
    spec['parent_job']=jid
    with db() as c:c.execute('INSERT INTO jobs(id,spec,status,stage,created,updated) VALUES(?,?,?,?,?,?)',(new,json.dumps(spec),'queued','Queued revision',time.time(),time.time()))
    return {'id':new}

@app.get('/media/{jid}/{name}')
def media(jid:str,name:str):
    job(jid)
    if name not in ['video.mp4','speech.wav','captions.srt','poster.webp','evidence.json','mouth-cues.json']:raise HTTPException(404)
    path=JOBS/jid/name
    if not path.is_file():raise HTTPException(404)
    return FileResponse(path,filename=name if name in ['captions.srt','evidence.json'] else None)

@app.get('/')
def home():return FileResponse(ROOT/'static/index.html')

app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
