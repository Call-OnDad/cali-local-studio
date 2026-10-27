"""Control-plane tests, separate from real server media integration checks."""
import os
import atexit
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

tmp=tempfile.TemporaryDirectory()
atexit.register(tmp.cleanup)
os.environ['STUDIO_DATA']=tmp.name
import app
from fastapi.testclient import TestClient
from renderer import pose_at

class Controls(unittest.TestCase):
    def setUp(self):
        app.STOP.clear()
        self.patch=patch.object(app,'worker',lambda:None);self.patch.start()
        self.ctx=TestClient(app.app,base_url='http://127.0.0.1:8780',client=('127.0.0.1',50000));self.client=self.ctx.__enter__()

    def tearDown(self):
        self.ctx.__exit__(None,None,None);self.patch.stop()

    def test_private_api(self):
        self.assertEqual(self.client.get('/api/jobs').status_code,200)
        with TestClient(app.app,base_url='http://192.168.1.10:8780',client=('203.0.113.4',50000)) as other:
            self.assertEqual(other.get('/api/jobs').status_code,403)
        self.assertEqual(self.client.get('/api/jobs',headers={'Host':'untrusted.example'}).status_code,403)

    def test_cross_origin_rejected(self):
        self.assertEqual(self.client.post('/api/jobs',json={'text':'Hello'},headers={'Origin':'https://untrusted.example'}).status_code,403)

    def test_input_validation(self):
        for spec in [{'text':'   '},{'text':'hello','character':'unknown'},{'text':'hello','format':'oops'},{'text':'hello','mouth':float('inf') if False else 999}]:
            self.assertEqual(self.client.post('/api/jobs',json=spec).status_code,422)

    def test_cancel_resume_and_invalid_retry(self):
        jid=self.client.post('/api/jobs',json={'text':'A short test.'}).json()['id']
        self.assertEqual(self.client.post(f'/api/jobs/{jid}/retry',json={}).status_code,409)
        self.assertEqual(self.client.post(f'/api/jobs/{jid}/cancel',json={}).status_code,200)
        self.assertEqual(self.client.get(f'/api/jobs/{jid}').json()['status'],'cancelled')
        self.assertEqual(self.client.post(f'/api/jobs/{jid}/retry',json={}).status_code,200)
        self.client.post(f'/api/jobs/{jid}/cancel',json={})

    def test_cue_revision_preserves_original(self):
        jid=self.client.post('/api/jobs',json={'text':'Hello again.'}).json()['id']
        app.update(jid,status='complete')
        folder=app.JOBS/jid;folder.mkdir(exist_ok=True)
        (folder/'speech.wav').write_bytes(b'original-audio')
        (folder/'mouth-cues.json').write_text('{"mouthCues": []}')
        bad={'cues':[{'start':1,'end':2,'value':'A'},{'start':.5,'end':1.5,'value':'D'}]}
        self.assertEqual(self.client.post(f'/api/jobs/{jid}/cues',json=bad).status_code,422)
        good={'cues':[{'start':0,'end':.5,'value':'X'},{'start':.5,'end':1,'value':'D'}]}
        response=self.client.post(f'/api/jobs/{jid}/cues',json=good)
        self.assertEqual(response.status_code,200)
        new=response.json()['id']
        self.assertNotEqual(new,jid)
        self.assertFalse((folder/'cue-edits.json').exists())
        self.assertEqual((app.JOBS/new/'speech.wav').read_bytes(),b'original-audio')
        self.client.post(f'/api/jobs/{new}/cancel',json={})

    def test_path_and_missing_job(self):
        self.assertEqual(self.client.get('/media/not-a-job/video.mp4').status_code,404)
        self.assertEqual(self.client.get('/api/jobs/not-a-job').status_code,404)

    def test_mouth_boundary_is_continuous(self):
        cues=[{'start':0,'end':.2,'value':'A'},{'start':.2,'end':.25,'value':'D'},{'start':.25,'end':.8,'value':'F'}]
        for boundary in [.2,.25]:
            before=pose_at(boundary-.00001,cues);after=pose_at(boundary+.00001,cues)
            self.assertLess(max(abs(a-b) for a,b in zip(before,after)),.003)
        self.assertEqual(pose_at(-.1,cues),(0,0,0))
        self.assertEqual(pose_at(.9,cues),(0,0,0))

if __name__=='__main__':unittest.main()
