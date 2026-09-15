import ast
import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
q=module('tolf_quick',ROOT/'setup/quick/tolf_quick.py')
p=module('quick_installer',ROOT/'setup/quick/install-template.py')
USER='0888048c-ac6e-44d2-8aed-9857aa31e9ed'

class QuickTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'db'
  with sqlite3.connect(self.db) as c:
   c.execute('CREATE TABLE users(id TEXT PRIMARY KEY)');c.execute('INSERT INTO users VALUES (?)',(USER,))
  self.calls=[];self.record=None;self.failure=False;self.app=FastAPI()
  def auth(request):
   if request.headers.get('x-test-user')!=USER:raise HTTPException(401)
   return USER
  def create(request,selection):
   auth(request);self.calls.append(('create',selection));self.record=True
   if self.failure: self.failure=False;raise HTTPException(502)
   return {'profileUrl':'https://config.tolf.is/p/test'}
  def profile(request,selection):
   auth(request);self.calls.append(('profile',selection));return {'profileUrl':'https://config.tolf.is/p/test'}
  @self.app.post('/windows/devices')
  def windows(request:Request,payload:dict):
   auth(request);self.calls.append(('windows',payload))
   if self.failure:self.failure=False;raise HTTPException(502)
   return {'profileUrl':'https://api.tolf.is/windows/p/test'}
  q.install(self.app,{'DB':self.db,'authenticated_user_id':auth,'ORIGIN':'https://vpn.tolf.is',
                      'vpn_record':lambda u:self.record,'vpn_create':create,'vpn_profile':profile})
  self.client=TestClient(self.app)
  self.headers={'origin':'https://vpn.tolf.is','x-test-user':USER}
 def tearDown(self):self.client.close();self.tmp.cleanup()
 def post(self,platform='ios',server='moscow',headers=None):
  return self.client.post('/quick-setup/prepare',headers=self.headers if headers is None else headers,json={'platform':platform,'server':server,'language':'ru'})
 def test_auth_and_origin(self):
  self.assertEqual(self.post(headers={}).status_code,403)
  self.assertEqual(self.post(headers={'origin':'https://vpn.tolf.is'}).status_code,401)
  self.assertEqual(self.calls,[])
 def test_moscow_defaults(self):
  self.assertEqual(self.post().status_code,200)
  selection=self.calls[0][1];self.assertEqual(selection['server'],'moscow');self.assertEqual(selection['localId'],'')
  self.assertFalse(selection['onDemandEnabled']);self.assertEqual(selection['dnsMode'],'tolf')
 def test_retry_after_lost_create(self):
  self.failure=True;self.assertEqual(self.post().status_code,502)
  self.assertEqual(self.post().status_code,200)
  self.assertEqual([c[0] for c in self.calls],['create','profile'])
 def test_retry_windows_stable_id(self):
  self.failure=True;self.assertEqual(self.post('windows').status_code,502)
  self.assertEqual(self.post('windows').status_code,200)
  self.assertEqual(self.calls[0][1]['requestId'],self.calls[1][1]['requestId'])
 def test_selection_cannot_change_after_reservation(self):
  self.post();self.assertEqual(self.post(server='riga').status_code,409);self.assertEqual(len(self.calls),1)
 def test_resume_contains_no_secrets(self):
  self.post();r=self.client.get('/quick-setup/status',headers=self.headers)
  self.assertEqual(r.json(),{'setup':{'platform':'ios','server':'moscow','state':'ready'}})
  self.assertEqual(r.headers['cache-control'],'no-store')
 def test_invalid_input_no_side_effects(self):
  self.assertEqual(self.post(server='uk').status_code,400);self.assertEqual(self.calls,[])
 def test_existing_vpn_uses_profile(self):
  self.record=True;self.post('android','riga');self.assertEqual(self.calls[0][0],'profile')
 def test_parallel_prepare_rejected(self):
  import fcntl
  with open(self.db.parent/'quick-locks'/USER,'a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   self.assertEqual(self.post().status_code,409)
   self.assertEqual(self.calls,[])
 def test_public_access(self):
  self.assertEqual(q.allowed_servers(self.db,USER),['riga','moscow'])
 def test_registration_cookie(self):
  import datetime
  with sqlite3.connect(self.db) as c:c.execute('CREATE TABLE sessions(token_hash BLOB,user_id TEXT,created_at TEXT,expires_at TEXT)')
  ns={'DB':self.db,'utc_now':lambda:datetime.datetime.now(datetime.timezone.utc),'utc_iso':lambda d:d.isoformat(),'SESSION_DAYS':30,'SESSION_COOKIE':'tolf_session'}
  r=q.registration_session({'userId':USER,'recoveryCode':'TEST'},ns)
  cookie=r.headers['set-cookie'];self.assertIn('HttpOnly',cookie);self.assertIn('Secure',cookie);self.assertIn('SameSite=lax',cookie)
  with sqlite3.connect(self.db) as c:self.assertEqual(c.execute('SELECT user_id FROM sessions').fetchone()[0],USER)

class PatchTests(unittest.TestCase):
 SOURCE='''import tolf_promos

def requested_server(user_id, payload):
    server = (payload or {}).get("server", "riga")
    if server not in ("riga", "moscow"):
        raise HTTPException(400, "Invalid server")
    if server not in tolf_promos.allowed_servers(DB, user_id):
        raise HTTPException(403, "Moscow access requires a promo code")
    return server

async def passkey_register_finish(request):
    verification = verify_registration_response()
    return {"status": "ok", "userId": user_id, "recoveryCode": recovery_code}
'''
 def test_patch_is_guarded_and_idempotent(self):
  new=p.patch(self.SOURCE);ast.parse(new);self.assertEqual(p.patch(new),new)
  self.assertIn('provision_on_riga("grant-moscow", user_id)',new)
  self.assertIn('registration_session',new)
  with self.assertRaises(RuntimeError):p.patch('def other(): pass')
 def test_suspension_not_overridden(self):
  new=p.patch(self.SOURCE)
  ns={'HTTPException':HTTPException,'DB':None,'tolf_quick':q,'provision_on_riga':lambda *args:(_ for _ in ()).throw(HTTPException(403,'Suspended'))}
  tree=ast.parse(new);func=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
  exec(compile(ast.Module(body=[func],type_ignores=[]),'test','exec'),ns)
  with self.assertRaises(HTTPException):ns['requested_server'](USER,{'server':'moscow'})
 def test_live_public_server_variant(self):
  tree=ast.parse(self.SOURCE);old=ast.get_source_segment(self.SOURCE,tree.body[1])
  source=self.SOURCE.replace(old,p.PUBLIC_REQUESTED_SERVER.strip())
  new=p.patch(source);self.assertEqual(p.patch(new),new)
  calls=[]
  ns={'HTTPException':HTTPException,'provision_on_riga':lambda *args:calls.append(args)}
  func=next(n for n in ast.parse(new).body if isinstance(n,ast.FunctionDef))
  exec(compile(ast.Module(body=[func],type_ignores=[]),'test','exec'),ns)
  self.assertEqual(ns['requested_server'](USER,{}),'riga');self.assertEqual(calls,[])
  self.assertEqual(ns['requested_server'](USER,{'server':'moscow'}),'moscow')
  self.assertEqual(calls,[('grant-moscow',USER)])
  with self.assertRaises(HTTPException):ns['requested_server'](USER,{'server':'unknown'})
  with self.assertRaises(RuntimeError):p.patch(source.replace('return server','return "riga"'))
if __name__=='__main__':unittest.main()
