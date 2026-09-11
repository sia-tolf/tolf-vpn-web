import contextlib, io, json, os, sqlite3, tempfile, types, uuid, zipfile
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/"setup/windows"))
import tolf_windows as w


def test_lifecycle(monkeypatch):
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp); directory=root/'profiles'; directory.mkdir()
  installer=root/'TOLF-Setup.exe';installer.write_bytes(b'MZ_TEST_EXECUTABLE_NO_CREDENTIALS');monkeypatch.setattr(w,'INSTALLER',installer)
  remote={}; calls=[]
  def provision(action, device_id, server='riga', local_id=None):
   calls.append((action,device_id))
   if action=='create': remote.setdefault(device_id, {'username':'user_'+uuid.UUID(device_id).hex,'password':'TEST_ONLY_4E7A'})
   if action in ('create','profile'): return {**remote[device_id], 'server':server,'localId':local_id}
   return {'status':'ok'}
  def remove(device_id,expected): remote.pop(device_id,None)
  def auth(request):
   value=request.headers.get('x-test-user')
   if not value: raise HTTPException(401,'Not authenticated')
   return value
  def write(path,content):
   path.write_bytes(content); path.chmod(0o600)
  profiles=types.SimpleNamespace(PROFILE_DIR=directory, initialize=lambda:None, _valid_secret=lambda s:isinstance(s,str) and bool(s), _atomic_write=write)
  ctx={'DB':str(root/'db'),'authenticated_user_id':auth,'provision_on_riga':provision,'remove_provisioned_vpn':remove,'tolf_profiles':profiles,'tolf_promos':types.SimpleNamespace(account_operation=lambda *a:contextlib.nullcontext())}
  app=FastAPI();w.install(app,ctx)
  a,b=str(uuid.uuid4()),str(uuid.uuid4());h={'x-test-user':a};hb={'x-test-user':b}
  with TestClient(app) as c:
   assert c.get('/windows/devices').status_code==401
   assert c.get('/windows/devices',headers=h).json()=={'devices':[]}
   assert not remote # reads and platform capabilities do not provision
   payload={'requestId':str(uuid.uuid4()),'name':'Office <PC>','language':'ru'}
   r=c.post('/windows/devices',headers=h,json=payload);assert r.status_code==200,r.text
   data=r.json();device=data['device']['id'];url=data['profileUrl'].replace('https://api.tolf.is','')
   assert data['device']['username']!='user_'+uuid.UUID(a).hex
   retry=c.post('/windows/devices',headers=h,json=payload).json();assert retry['device']['id']==device and len(remote)==1
   assert c.get('/windows/devices',headers=hb).json()=={'devices':[]}
   for action in ['profile','delete']:
    assert c.post(f'/windows/devices/{device}/{action}',headers=hb,json={}).status_code==404
   page=c.get(url);assert page.status_code==200 and '&lt;PC&gt;' in page.text and 'TEST_ONLY' not in page.text
   download=c.get(url+'/download');assert download.status_code==200
   assert download.content==installer.read_bytes()
   assert '.exe' in download.headers['content-disposition']
   assert b'TEST_ONLY' not in download.content
   response=c.post(url+'/settings');assert response.status_code==200
   assert response.json()['username']==data['device']['username']
   assert 'no-store' in response.headers['cache-control']
   assert c.get(url+'/settings').status_code==405
   assert 'ZIP' not in page.text and 'Install-TOLF.cmd' not in page.text
   assert 'id="download"' in page.text and ' hidden>' in page.text
   assert 'id="personal-link"' in page.text and 'navigator.share' in page.text
   dbbytes=Path(ctx['DB']).read_bytes(); assert b'TEST_ONLY' not in dbbytes
   # Reissue keeps credentials and owner. Expired packages are rejected.
   assert c.post(f'/windows/devices/{device}/profile',headers=h,json={'language':'lv'}).status_code==200
   token=url.rsplit('/',1)[1];path=directory/(token+'.json');meta=json.loads(path.read_text());meta['expiresAt']='2000-01-01T00:00:00+00:00';path.write_text(json.dumps(meta))
   assert c.get(url).status_code==410
   assert c.post(url+'/settings').status_code==410
   assert c.get(url+'/download').status_code==410
   assert c.post(f'/windows/devices/{device}/delete',headers=h).status_code==200
   assert c.post(f'/windows/devices/{device}/delete',headers=h).status_code==200
   assert c.post('/windows/devices',headers=h,json=payload).status_code==410
   assert not remote and c.get('/windows/devices',headers=h).json()=={'devices':[]}
   # Lost provisioning response leaves a resumable record, not a duplicate.
   original=ctx['provision_on_riga']; failed=[False]
   def fail_once(*args):
    result=original(*args)
    if args[0]=='create' and not failed[0]: failed[0]=True;raise HTTPException(502,'lost response')
    return result
   ctx['provision_on_riga']=fail_once
   p={'requestId':str(uuid.uuid4()),'name':'Retry PC'}
   assert c.post('/windows/devices',headers=h,json=p).status_code==502
   row=c.get('/windows/devices',headers=h).json()['devices'][0];assert row['state']=='provisioning'
   assert c.post('/windows/devices/'+row['id']+'/profile',headers=h,json={}).status_code==200
   assert len(remote)==1
   w.delete_all(a);assert not remote
