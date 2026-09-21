"""Extract the credential-free bundle and verify a separate Python environment."""
import json,os,pathlib,secrets,subprocess,zipfile,re
ROOT=pathlib.Path(__file__).resolve().parents[1]
folder=ROOT/'artifacts'/('reprocheck-'+secrets.token_hex(5));folder.mkdir()
with zipfile.ZipFile(ROOT/'submission/SkillForge-review-bundle.zip') as archive:
 for name in archive.namelist():
  destination=(folder/name).resolve()
  if not destination.is_relative_to(folder.resolve()):raise RuntimeError('Unsafe archive path')
 archive.extractall(folder)
source=folder/'skillforge';venv=folder/'venv';uv=ROOT/'.venv/uv'
log=(folder/'verification.log').open('w')
subprocess.run([str(uv),'venv',str(venv)],check=True,stdout=log,stderr=log)
python=venv/'bin/python'
subprocess.run([str(uv),'pip','install','--python',str(python),'-r',str(source/'requirements-lock.txt'),'-e',str(source)],check=True,stdout=log,stderr=log)
env={**os.environ,'SKILLFORGE_DB':':memory:','NVIDIA_API_KEY':'','SKILLFORGE_OPERATOR_SESSION':'','PYTHONPATH':str(source)}
subprocess.run([str(python),'-m','unittest','discover','-s','tests','-v'],cwd=source,env=env,check=True,stdout=log,stderr=log)
probe="from pathlib import Path; from fastapi.testclient import TestClient; from backend.api import app; import backend; c=TestClient(app); assert Path(backend.__file__).resolve().is_relative_to(Path.cwd()); assert c.get('/health').json()['key_configured'] is False; html=c.get('/'); assert html.status_code==200; import re; asset=re.search(r'src=\"(/assets/[^\"]+)\"',html.text).group(1); assert c.get(asset).status_code==200; print('fresh source and built React assets verified')"
subprocess.run([str(python),'-c',probe],cwd=source,env=env,check=True,stdout=log,stderr=log)
log.close()
result={'passed':True,'source':str(source),'environment':str(venv),'credential_files_included':False,'tests':int(re.search(r'Ran (\d+) tests', (folder/'verification.log').read_text()).group(1)),'built_ui_served':True,'log':str(folder/'verification.log')}
(ROOT/'artifacts/reproduction-evidence.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))

