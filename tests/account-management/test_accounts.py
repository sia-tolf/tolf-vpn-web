import ast
import asyncio
import fcntl
import hashlib
import importlib.util
import json
import os
import sqlite3
import tempfile
import unittest
import uuid
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException, Request

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


module=load('account_management',ROOT/'setup/admin/tolf_account_admin.py')
patcher=load('account_patch',ROOT/'setup/admin/account_management_patch.py')


def function(source, name, ns):
    node=next(n for n in ast.walk(ast.parse(source)) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
    node.decorator_list=[]
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'<tested-production-function>','exec'),ns)
    return ns[name]


class AccountsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.path=str(self.root/'db')
        self.owner,self.target,self.protected,self.other=[str(uuid.uuid4()) for _ in range(4)]
        self.calls=[];self.fail_ike=False;self.fail_oc=False;self.locks=0
        with closing(sqlite3.connect(self.path)) as c,c:
            c.executescript('''
            CREATE TABLE users(id TEXT PRIMARY KEY,created_at TEXT,webauthn_user_id BLOB,recovery_code_hash BLOB);
            CREATE TABLE managed_users(number INTEGER,account_id TEXT,vpn_username TEXT,deleted_at TEXT,vpn_active INTEGER);
            CREATE TABLE admin_roles(user_id TEXT);CREATE TABLE admin_audit(id INTEGER PRIMARY KEY,actor TEXT,action TEXT,target TEXT,created_at TEXT);
            CREATE TABLE vpn_imports(user_id TEXT,protected INTEGER);CREATE TABLE vpn_access(user_id TEXT,vpn_username TEXT,created_at TEXT,server TEXT);
            CREATE TABLE windows_devices(id TEXT,user_id TEXT,name TEXT,username TEXT,state TEXT,created_at TEXT);
            CREATE TABLE windows_device_nodes(device_id TEXT,server TEXT);
            CREATE TABLE passkeys(credential_id BLOB PRIMARY KEY,user_id TEXT,public_key BLOB,sign_count INTEGER,created_at TEXT,name TEXT);
            CREATE TABLE sessions(token_hash BLOB,user_id TEXT,created_at TEXT,expires_at TEXT);
            CREATE TABLE challenges(id TEXT,user_id TEXT,kind TEXT,challenge BLOB,created_at TEXT,webauthn_user_id BLOB,passkey_name TEXT);
            CREATE TABLE oc_devices(id TEXT,user_id TEXT,username TEXT,state TEXT,expires_at TEXT,revoked_at TEXT);
            CREATE TABLE oc_import_grants(user_id TEXT);CREATE TABLE oc_policy_retries(device_id TEXT);
            CREATE TABLE live_payment_credits(user_id TEXT,bytes INTEGER);
            CREATE TABLE dns_accounts(user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE);
            CREATE TABLE dns_credentials(id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id) ON DELETE CASCADE);
            CREATE TABLE quick_setups(user_id TEXT REFERENCES users(id) ON DELETE CASCADE);
            CREATE TABLE vpn_personal_routing(user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE);
            CREATE TABLE vpn_personal_routing_delivery(account_id TEXT,intent_json TEXT);
            CREATE TABLE oc_setup_links(user_id TEXT,token_hash BLOB);
            CREATE TRIGGER registry_delete AFTER DELETE ON users BEGIN UPDATE managed_users SET deleted_at='deleted',vpn_active=0 WHERE account_id=OLD.id; END;
            CREATE TRIGGER oc_delete AFTER DELETE ON users BEGIN UPDATE oc_devices SET state='revoking',revoked_at='2026-10-26T00:00:00+00:00' WHERE user_id=OLD.id AND state IN ('active','pending'); DELETE FROM oc_import_grants WHERE user_id=OLD.id; END;
            ''')
            for i,uid in enumerate([self.owner,self.target,self.protected,self.other],1):
                c.execute('INSERT INTO users VALUES(?,?,?,?)',(uid,'2026-10-26',b'web'+uid.encode(),b'private'))
                c.execute('INSERT INTO managed_users VALUES(?,?,?,NULL,1)',(i,uid,'user'+str(i)))
                c.execute('INSERT INTO vpn_imports VALUES(?,?)',(uid,int(uid==self.protected)))
                c.execute('INSERT INTO vpn_access VALUES(?,?,?,?)',(uid,'user'+str(i),'2026-10-26','riga'))
                c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(b'token',uid,'2026-10-26','2099-01-01'))
                c.execute('INSERT INTO passkeys VALUES(?,?,?,?,?,?)',(uid.encode(),uid,b'public',0,'2026-10-26','Key'))
                c.execute('INSERT INTO oc_devices VALUES(?,?,?,?,?,NULL)',('device'+str(i),uid,'oc'+str(i),'revoking' if uid==self.other else 'active','2099-01-01T00:00:00+00:00'))
                c.execute('INSERT INTO oc_import_grants VALUES(?)',(uid,))
                c.execute('INSERT INTO dns_accounts VALUES(?)',(uid,));c.execute('INSERT INTO dns_credentials VALUES(?,?)',(uid,uid))
                c.execute('INSERT INTO quick_setups VALUES(?)',(uid,));c.execute('INSERT INTO vpn_personal_routing VALUES(?)',(uid,))
                c.execute('INSERT INTO vpn_personal_routing_delivery VALUES(?,?)',(uid,'private rules'));c.execute('INSERT INTO oc_setup_links VALUES(?,?)',(uid,b'private link'))
            c.execute('INSERT INTO admin_roles VALUES(?)',(self.owner,))
            c.execute('INSERT INTO live_payment_credits VALUES(?,?)',(self.target,50000000000))
        def auth(request):
            uid=request.headers.get('x-fixture-user')
            if not uid:raise HTTPException(401,'not_authenticated')
            return uid
        @contextmanager
        def account_operation(path,uid):
            self.assertEqual(path,self.path);self.assertEqual(self.locks,0,'account lock cannot be nested')
            with closing(sqlite3.connect(path)) as c:
                if not c.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone():raise HTTPException(404,'not_found')
            self.locks+=1
            try:yield
            finally:self.locks-=1
        def remove_vpn(uid,name):
            self.calls.append(('ike',uid))
            if self.fail_ike:raise HTTPException(503,'node_unavailable')
        def revoke(username):
            self.calls.append(('oc',username))
            if self.fail_oc:raise HTTPException(503,'node_unavailable')
        def vpn_record(uid):
            with closing(sqlite3.connect(self.path)) as c:return c.execute('SELECT vpn_username FROM vpn_access WHERE user_id=?',(uid,)).fetchone()
        context={'DB':self.path,'ORIGIN':'https://vpn.tolf.is','authenticated_user_id':auth,
                 'tolf_promos':SimpleNamespace(account_operation=account_operation,detach_account=lambda c,u:None),
                 'tolf_invitations':SimpleNamespace(before_account_delete=lambda u:None),
                 'tolf_windows':SimpleNamespace(delete_all=lambda u:self.calls.append(('windows',u))),
                 'vpn_record':vpn_record,'remove_provisioned_vpn':remove_vpn,'provision_on_riga':lambda action,u:self.calls.append((action,u)),
                 'sqlite3':sqlite3,'HTTPException':HTTPException}
        oc_path=ROOT/'server-candidate/tolf_anyconnect.py'
        oc=oc_path.read_text() if oc_path.exists() else patcher.anyconnect_source((ROOT/'tests/account-management/fixtures/anyconnect.py').read_text())
        namespace={'os':os,'fcntl':fcntl,'sqlite3':sqlite3,'closing':closing,'directory':self.root,'db':self.path,'utc_now':lambda:datetime.now(timezone.utc),'node':SimpleNamespace(revoke=revoke),'published_crl':lambda *a:self.calls.append(('crl',)),'authority':object(),'HTTPException':HTTPException}
        context['oc_reconcile_account']=function(oc,'reconcile',namespace)
        main_path=ROOT/'server-candidate/main.py'
        main=main_path.read_text() if main_path.exists() else patcher.main_source((ROOT/'tests/account-management/fixtures/main.py').read_text())
        context['delete_account_data']=function(main,'delete_account_data',context)
        self.context=context;self.app=FastAPI();module.install(self.app,context);self.a=self.app.state.account_management
        password_path=ROOT/'server-candidate/tolf_password_auth.py'
        if not password_path.exists():password_path=ROOT/'setup/password-auth/tolf_password_auth.py'
        password=load('password_fixture',password_path)
        context.update({'utc_now':lambda:datetime.now(timezone.utc),'utc_iso':lambda d:d.isoformat(),'SESSION_DAYS':30,'SESSION_COOKIE':'tolf_session','generate_recovery_code':lambda:'TEST-RECOVERY','recovery_code_hash':lambda c:hashlib.sha256(c.encode()).digest()})
        password.install(self.app,context)

    def tearDown(self):self.temp.cleanup()

    def request(self,user=None,origin='https://vpn.tolf.is',body=None):
        headers={'origin':origin,'content-type':'application/json'}
        if user:headers['x-fixture-user']=user
        async def receive():return {'type':'http.request','body':json.dumps(body or {}).encode(),'more_body':False}
        return Request({'type':'http','method':'POST','path':'/','headers':[(k.encode(),v.encode()) for k,v in headers.items()],'client':('127.0.0.1',1234),'query_string':b''},receive)

    def payload(self,number=2,**kwargs):return {'requestId':str(uuid.uuid4()),'confirm':'DELETE','number':number,**kwargs}

    def status(self,code,fn):
        with self.assertRaises(HTTPException) as e:fn()
        self.assertEqual(e.exception.status_code,code)

    def test_explicit_trial_only_idempotent_and_kept_after_purchase(self):
        with self.a.db() as c:
            self.a.record_trial(c,self.target,{},'password')
            self.assertIsNone(self.a.metadata(c,self.target)['trialRegistration'])
            self.a.record_trial(c,self.target,{'registrationPurpose':'trial'},'password')
            first=self.a.metadata(c,self.target)['trialRegistration']
            self.a.record_trial(c,self.target,{'registrationPurpose':'trial'},'passkey')
            self.assertEqual(self.a.metadata(c,self.target)['trialRegistration'],first)
            self.assertTrue(first['hasPaidTraffic'])
        self.assertEqual(self.a.trial_summary()['activeTrialAccounts'],1)

    def test_password_registration_marks_only_committed_trial_account(self):
        route=next(r.endpoint for r in self.app.routes if r.path=='/password/register')
        for name,purpose in [('trial-user','trial'),('ordinary-user',None)]:
            payload={'username':name,'password':'Unpredictable!9-Lime-86-Cloud'}
            if purpose:payload['registrationPurpose']=purpose
            route(self.request(),payload)
            with self.a.db() as c:
                uid=c.execute('SELECT user_id FROM account_passwords WHERE username=?',(name,)).fetchone()[0]
                marked=c.execute('SELECT 1 FROM account_trial_registrations WHERE user_id=?',(uid,)).fetchone()
                self.assertEqual(bool(marked),purpose is not None)
        self.status(400,lambda:route(self.request(),{'username':'invalid-purpose','password':'Unpredictable!9-Lime-86-Cloud','registrationPurpose':'anything'}))
        with self.a.db() as c:self.assertIsNone(c.execute('SELECT 1 FROM account_passwords WHERE username=?',('invalid-purpose',)).fetchone())

    def test_deletion_guards_do_not_touch_any_users_or_nodes(self):
        tests=[(401,self.request(),self.target,self.payload()),(403,self.request(self.other),self.target,self.payload()),(403,self.request(self.owner,'https://evil.example'),self.target,self.payload()),(409,self.request(self.owner),self.owner,self.payload(1)),(409,self.request(self.owner),self.protected,self.payload(3)),(409,self.request(self.owner),self.target,self.payload(99)),(400,self.request(self.owner),self.target,self.payload(confirm='NO'))]
        for code,request,target,payload in tests:self.status(code,lambda:self.a.delete(request,target,payload))
        self.assertEqual(self.calls,[])
        with self.a.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0],4)

    def test_deletes_only_target_and_preserves_payment_history(self):
        with self.a.db() as c:self.a.record_trial(c,self.target,{'registrationPurpose':'trial'},'password')
        payload=self.payload();result,status=self.a.delete(self.request(self.owner),self.target,payload)
        self.assertEqual(status,200);self.assertTrue(result['deleted']);self.assertFalse(result['vpnRevocationPending'])
        with self.a.db() as c:
            self.assertIsNone(c.execute('SELECT 1 FROM users WHERE id=?',(self.target,)).fetchone())
            self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0],3)
            for table in ['sessions','passkeys','vpn_access','account_trial_registrations','dns_accounts','dns_credentials','quick_setups','vpn_personal_routing','oc_setup_links']:
                self.assertEqual(c.execute('SELECT COUNT(*) FROM '+table+' WHERE user_id=?',(self.target,)).fetchone()[0],0)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM dns_credentials').fetchone()[0],3)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM vpn_personal_routing_delivery WHERE account_id=?',(self.target,)).fetchone()[0],0)
            self.assertEqual(c.execute('SELECT bytes FROM live_payment_credits WHERE user_id=?',(self.target,)).fetchone()[0],50000000000)
            self.assertEqual(c.execute('SELECT state FROM oc_devices WHERE user_id=?',(self.target,)).fetchone()[0],'revoked')
            self.assertEqual(c.execute('SELECT state FROM oc_devices WHERE user_id=?',(self.other,)).fetchone()[0],'revoking')
            self.assertIsNotNone(c.execute('SELECT deleted_at FROM managed_users WHERE account_id=?',(self.target,)).fetchone()[0])
        calls=list(self.calls);repeated,_=self.a.delete(self.request(self.owner),self.target,payload)
        self.assertEqual(repeated,result);self.assertEqual(self.calls,calls)
        self.assertEqual([x for x in self.calls if x[0]=='oc'],[('oc','oc2')])

    def test_node_failure_keeps_account_and_allows_explicit_retry(self):
        payload=self.payload();self.fail_ike=True
        self.status(502,lambda:self.a.delete(self.request(self.owner),self.target,payload))
        with self.a.db() as c:
            self.assertIsNotNone(c.execute('SELECT 1 FROM users WHERE id=?',(self.target,)).fetchone())
            self.assertEqual(c.execute('SELECT state FROM admin_account_delete_jobs').fetchone()[0],'failed')
        self.fail_ike=False;result,_=self.a.delete(self.request(self.owner),self.target,payload);self.assertTrue(result['deleted'])

    def test_restart_after_deletion_commit_recovers_without_repeating_node_calls(self):
        payload=self.payload()
        with self.a.db() as c:c.execute('INSERT INTO admin_account_delete_jobs VALUES(?,?,?,?,?,?,?,?)',(payload['requestId'],self.owner,self.target,2,'running',None,0,0))
        self.context['delete_account_data'](self.target)
        calls=list(self.calls)
        result,status=self.a.delete(self.request(self.owner),self.target,payload)
        self.assertEqual(status,200);self.assertTrue(result['deleted']);self.assertEqual(self.calls,calls)

    def test_anyconnect_failure_is_reported_as_pending_and_can_be_reconciled(self):
        self.fail_oc=True
        result,_=self.a.delete(self.request(self.owner),self.target,self.payload())
        self.assertTrue(result['deleted']);self.assertTrue(result['vpnRevocationPending'])
        self.fail_oc=False;self.context['oc_reconcile_account'](self.target)
        with self.a.db() as c:self.assertEqual(c.execute('SELECT state FROM oc_devices WHERE user_id=?',(self.target,)).fetchone()[0],'revoked')

    def test_private_routes_and_existing_trial_confirmation(self):
        summary=next(r.endpoint for r in self.app.routes if r.path=='/admin/trial-registrations')
        self.status(401,lambda:summary(self.request()));self.status(403,lambda:summary(self.request(self.other)))
        register=next(r.endpoint for r in self.app.routes if r.path=='/account/trial-registration' and 'POST' in r.methods)
        self.status(400,lambda:register(self.request(self.target),{'confirm':'NO'}))
        response=register(self.request(self.target),{'confirm':'TRIAL_REGISTRATION'})
        self.assertFalse(json.loads(response.body)['trialPackageIssuance']);self.assertIn('no-store',response.headers['cache-control'])

    def test_passkey_trial_marker_follows_successful_verification(self):
        path=ROOT/'server-candidate/main.py'
        source=path.read_text() if path.exists() else patcher.main_source((ROOT/'tests/account-management/fixtures/main.py').read_text())
        ns=self.context
        ns.update({'Request':Request,'RP_ID':'vpn.tolf.is','tolf_quick':SimpleNamespace(registration_session=lambda data,context:data)})
        ns['verify_registration_response']=lambda **kwargs:SimpleNamespace(credential_id=uuid.uuid4().bytes,credential_public_key=b'public',sign_count=0)
        finish=function(source,'passkey_register_finish',ns)
        for purpose in ('trial',None):
            uid,challenge=str(uuid.uuid4()),str(uuid.uuid4())
            with self.a.db() as c:c.execute('INSERT INTO challenges VALUES(?,?,?,?,?,?,?)',(challenge,uid,'register',b'challenge','2026-10-26',uuid.uuid4().bytes,'Device'))
            payload={'challengeId':challenge,'credential':{'id':'fixture'}}
            if purpose:payload['registrationPurpose']=purpose
            asyncio.run(finish(self.request(body=payload)))
            with self.a.db() as c:self.assertEqual(bool(c.execute('SELECT 1 FROM account_trial_registrations WHERE user_id=?',(uid,)).fetchone()),purpose is not None)
        uid,challenge=str(uuid.uuid4()),str(uuid.uuid4())
        with self.a.db() as c:c.execute('INSERT INTO challenges VALUES(?,?,?,?,?,?,?)',(challenge,uid,'register',b'challenge','2026-10-26',uuid.uuid4().bytes,'Device'))
        def invalid(**kwargs):raise ValueError('verification failed')
        ns['verify_registration_response']=invalid
        self.status(400,lambda:asyncio.run(finish(self.request(body={'challengeId':challenge,'credential':{'id':'bad'},'registrationPurpose':'trial'}))))
        with self.a.db() as c:self.assertIsNone(c.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone())

    def test_admin_account_list_metadata_and_trial_filter(self):
        path=ROOT/'server-candidate/tolf_admin.py'
        if not path.exists():path=ROOT/'setup/admin/tolf_admin.py'
        source=path.read_text()
        ns={'CTX':self.context,'db':self.a.db,'require_admin':self.a.admin,'response':lambda data:data,'HTTPException':HTTPException,'Request':Request,'datetime':datetime,'timezone':timezone}
        function(source,'user_record',ns);users=function(source,'users',ns)
        with self.a.db() as c:self.a.record_trial(c,self.target,{'registrationPurpose':'trial'},'password')
        selected=users(self.request(self.owner),trial='only')
        self.assertEqual(selected['total'],1);self.assertEqual(selected['users'][0]['id'],self.target)
        self.assertTrue(selected['users'][0]['trialRegistration']['hasPaidTraffic'])
        self.assertTrue(selected['users'][0]['deletion']['allowed'])
        self.assertEqual(users(self.request(self.owner))['total'],4)
        self.status(400,lambda:users(self.request(self.owner),trial='anything'))


if __name__=='__main__':unittest.main(verbosity=2)
