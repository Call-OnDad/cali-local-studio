"""Render actual new speech/video on a running studio. No mocks or API keys."""
import argparse
import json
import time
import httpx

p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8780');p.add_argument('--timeout',type=int,default=600);args=p.parse_args()
with httpx.Client(base_url=args.url,trust_env=False,timeout=30) as client:
    client.get('/api/system').raise_for_status()
    r=client.post('/api/jobs',json={'title':'Self-hosted smoke test','character':'human','voice':'local-cori','text':'Hello. This fresh speech and animated video were created on this server, using local software.'});r.raise_for_status();jid=r.json()['id']
    deadline=time.monotonic()+args.timeout
    while time.monotonic()<deadline:
        r=client.get('/api/jobs/'+jid);r.raise_for_status();job=r.json()
        if job['status']=='failed':raise SystemExit(job['error'])
        if job['status']=='complete':break
        time.sleep(2)
    else:raise SystemExit('Render timed out; inspect the job in the studio')
    r=client.get(f'/media/{jid}/evidence.json');r.raise_for_status();e=r.json()
    assert e['full_decode'] and e['fresh_audio'] and e['fresh_animation']
    assert e['cues']>2 and e['duration']>1
    print(json.dumps({'job':jid,'duration':e['duration'],'full_decode':e['full_decode'],'video_url':args.url+job['video_url']},indent=2))
