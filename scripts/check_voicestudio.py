from pathlib import Path
import io
import json
import os
import wave
import httpx

root=Path(__file__).resolve().parents[1]
data=Path(os.environ.get('STUDIO_DATA',str(root/'data')));data.mkdir(parents=True,exist_ok=True)
key=Path(os.environ.get('VOICESTUDIO_API_KEY_FILE',str(root/'private/voicestudio-key'))).read_text().strip()
url=os.environ.get('VOICESTUDIO_URL','http://127.0.0.1:3900').rstrip('/')
with httpx.Client(timeout=600,trust_env=False) as client:
    r=client.post(url+'/generate',headers={'Authorization':'Bearer '+key},data={'text':'Hello. This is a new local speech integration check.','language':'English','engine':'kittentts','preset_voice':'expr-voice-2-f','effect_preset':'raw','denoise':'false','postprocess_output':'false'})
    if not r.is_success:raise SystemExit(f'Local speech check failed: HTTP {r.status_code}')
    with wave.open(io.BytesIO(r.content)) as w:seconds=w.getnframes()/w.getframerate()
    if seconds<.2:raise SystemExit('Speech output was too short')
    (data/'voicestudio-ready.json').write_text(json.dumps({'tested':True,'engine':'kittentts','duration':seconds}))
    print('Local KittenTTS speech passed; presets enabled.')
