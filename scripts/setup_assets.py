"""Fetch free local assets with pinned SHA256 hashes. No account or API key."""
from pathlib import Path
import hashlib
import os
import platform
import shutil
import sys
import tempfile
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ASSETS={
 'cori':('cori','1899f98e5fb8310154f3c2973f4b8a929ba7245e722b3d3a85680b833d95f10d','e262c16d7f192f69d4edd6b4ef8a5915379e67495fcc402f1ab15eeb33da3d36'),
 'northern':('northern_english_male','57a219ae8e638873db7d18893304be5069c42868f392bb95c3ff17f0690d0689','69557ed3d974463453e9b0c09dd99a7ed0e52b8b87b64b357dbeeb2540a97d47'),
}
RHUBARB_SHA='a9a9074862cff47b2d59b8bf399a678a3b0b74f9452ad6ad94cb292913dd8667'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def fetch(url,path,expected=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and (not expected or sha(path)==expected):return
    temp=path.with_name(path.name+'.partial')
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Cali-Local-Studio-asset-setup'})
        with urllib.request.urlopen(req,timeout=120) as response,temp.open('wb') as out:
            shutil.copyfileobj(response,out)
        if expected and sha(temp)!=expected:
            raise RuntimeError('Checksum mismatch; upstream asset needs review')
        temp.replace(path)
        print('Installed',path.name)
    except Exception as exc:
        temp.unlink(missing_ok=True)
        raise RuntimeError(f'Could not install {path.name}: {type(exc).__name__}. Retry setup; do not bypass checksum checks.') from None

def models():
    folder=Path(os.environ.get('STUDIO_MODELS_DIR',str(ROOT/'models')))
    for name,(upstream,model_sha,config_sha) in ASSETS.items():
        base=f'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/{upstream}/medium'
        fetch(f'{base}/en_GB-{upstream}-medium.onnx',folder/f'{name}.onnx',model_sha)
        fetch(f'{base}/en_GB-{upstream}-medium.onnx.json',folder/f'{name}.onnx.json',config_sha)
        fetch(f'{base}/MODEL_CARD',folder/f'{name}-MODEL_CARD.md')

def rhubarb():
    if platform.system()!='Linux' or platform.machine() not in ['x86_64','amd64']:
        raise RuntimeError('Bundled Rhubarb installer supports Linux x86-64. Install a compatible Rhubarb yourself and set RHUBARB_PATH.')
    target=ROOT/'tools/rhubarb'
    if (target/'rhubarb').is_file():return
    archive=ROOT/'tools/rhubarb-1.14.0.zip'
    fetch('https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v1.14.0/Rhubarb-Lip-Sync-1.14.0-Linux.zip',archive,RHUBARB_SHA)
    with tempfile.TemporaryDirectory(dir=archive.parent) as temp:
        temp=Path(temp)
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                if not (temp/name).resolve().is_relative_to(temp.resolve()):raise RuntimeError('Unsafe archive path')
            z.extractall(temp)
        source=temp/'Rhubarb-Lip-Sync-1.14.0-Linux'
        shutil.copytree(source,target,dirs_exist_ok=True)
    (target/'rhubarb').chmod(0o755)
    archive.unlink()

if __name__=='__main__':
    option=sys.argv[1] if len(sys.argv)>1 else 'all'
    if option not in ['all','models','rhubarb']:raise SystemExit('Choose all, models or rhubarb')
    if option in ['all','models']:models()
    if option in ['all','rhubarb']:rhubarb()
    print('Local assets ready. Original model cards/licences remain with the files.')
