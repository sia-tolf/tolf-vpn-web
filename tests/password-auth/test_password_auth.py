import hashlib
import importlib.util
import secrets
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('password_auth',ROOT/'setup/password-auth/tolf_password_auth.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
SCHEMA='''
CREATE TABLE users(id TEXT PRIMARY KEY,created_at TEXT NOT NULL,webauthn_user_id BLOB,recovery_code_hash BLOB);
CREATE UNIQUE INDEX idx_users_webauthn_user_id ON users(webauthn_user_id);
CREATE TABLE sessions(token_hash BLOB PRIMARY KEY,user_id TEXT NOT NULL,created_at TEXT NOT NULL,expires_at TEXT NOT NULL);
CREATE TABLE challenges(id TEXT PRIMARY KEY,user_id TEXT,kind TEXT,challenge BLOB,created_at TEXT,webauthn_user_id BLOB,passkey_name TEXT);
CREATE TABLE passkeys(credential_id BLOB PRIMARY KEY,user_id TEXT,public_key BLOB,sign_count INTEGER,created_at TEXT,name TEXT);
'''
PASS='a long personal password 42'
NEW='another personal password 73'

class PasswordTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.db=str(Path(self.tmp.name)/'db')
        with sqlite3.connect(self.db) as con:con.executescript(SCHEMA)
        ns={'DB':self.db,'SESSION_COOKIE':'tolf_session','SESSION_DAYS':30,'ORIGIN':'https://vpn.tolf.is',
            'utc_now':lambda:datetime.now(timezone.utc),'utc_iso':lambda v:v.isoformat(),
            'generate_recovery_code':lambda:'TOLF-'+secrets.token_hex(16).upper(),
            'recovery_code_hash':lambda c:hashlib.sha256(c.strip().upper().encode()).digest()}
        self.app=FastAPI();mod.install(self.app,ns)
        # The existing API session contract (hashed cookie token, expiring database row).
        @self.app.get('/me')
        def me(request:Request):
            token=request.cookies.get('tolf_session','')
            with sqlite3.connect(self.db) as con:
                row=con.execute('SELECT user_id FROM sessions WHERE token_hash=? AND expires_at>?', (hashlib.sha256(token.encode()).digest(),ns['utc_iso'](ns['utc_now']()))).fetchone()
            if not row:raise HTTPException(401)
            return {'userId':row[0]}
        ns['authenticated_user_id']=lambda request:me(request)['userId']
        self.client=TestClient(self.app,base_url='https://api.tolf.is',headers={'Origin':ns['ORIGIN']})

    def post(self,path,body,status=200,client=None):
        r=(client or self.client).post('/password/'+path,json=body)
        self.assertEqual(r.status_code,status,r.text)
        return r

    def register(self,name='lena-work'):
        return self.post('register',{'username':name,'password':PASS})

    def rows(self,sql,args=()):
        with sqlite3.connect(self.db) as con:return con.execute(sql,args).fetchall()

    def test_registration_login_cookie_and_no_plaintext(self):
        r=self.register('Lena-Work');self.assertEqual(r.json()['username'],'lena-work')
        self.assertEqual(r.headers['cache-control'],'no-store')
        for flag in ['HttpOnly','Secure','SameSite=lax']:self.assertIn(flag,r.headers['set-cookie'])
        uid=self.client.get('/me').json()['userId']
        data=self.rows('SELECT salt,digest FROM account_passwords')[0]
        self.assertEqual(len(data[0]),16);self.assertEqual(len(data[1]),32)
        self.assertNotIn(PASS.encode(),Path(self.db).read_bytes())
        self.assertNotIn(r.json()['recoveryCode'].encode(),Path(self.db).read_bytes())
        self.assertEqual(self.rows('SELECT length(webauthn_user_id) FROM users'),[(32,)])
        self.client.cookies.clear()
        self.post('login',{'username':'LENA-work','password':PASS})
        self.assertEqual(self.client.get('/me').json()['userId'],uid)
        self.post('login',{'username':'lena-work','password':'incorrect'},401)
        self.post('login',{'username':'unknown','password':'incorrect'},401)

    def test_duplicate_and_unique_salts(self):
        self.register();self.register('another-user')
        self.post('register',{'username':'LENA-WORK','password':PASS},409)
        self.assertEqual(len(self.rows('SELECT id FROM users')),2)
        rows=self.rows('SELECT salt,digest FROM account_passwords')
        self.assertNotEqual(rows[0][0],rows[1][0]);self.assertNotEqual(rows[0][1],rows[1][1])

    def test_reset_single_use_and_session_revocation(self):
        code=self.register().json()['recoveryCode'];old=self.client.cookies.get('tolf_session')
        uid=self.client.get('/me').json()['userId']
        with sqlite3.connect(self.db) as con:
            con.execute("INSERT INTO challenges(id,user_id,kind) VALUES ('pending',?,'passkey_add')",(uid,))
            con.execute("INSERT INTO passkeys(credential_id,user_id) VALUES (?,?)",(b'existing-key',uid))
        body={'username':'lena-work','password':NEW,'recoveryCode':code}
        r=self.post('recover',body);self.assertNotEqual(r.json()['recoveryCode'],code)
        self.post('recover',body,401)
        self.assertEqual(self.rows('SELECT count(*) FROM sessions'),[(1,)])
        self.assertEqual(self.rows('SELECT count(*) FROM challenges'),[(0,)])
        self.assertEqual(self.rows('SELECT count(*) FROM passkeys'),[(1,)])
        other=TestClient(self.app,base_url='https://api.tolf.is');other.cookies.set('tolf_session',old)
        self.assertEqual(other.get('/me').status_code,401)
        self.post('login',{'username':'lena-work','password':PASS},401)
        self.post('login',{'username':'lena-work','password':NEW})

    def test_recovery_cannot_change_other_user(self):
        code=self.register().json()['recoveryCode'];self.register('other-user')
        self.post('recover',{'username':'other-user','password':NEW,'recoveryCode':code},401)
        self.post('login',{'username':'other-user','password':PASS})

    def test_concurrent_reset_only_one_wins(self):
        code=self.register().json()['recoveryCode']
        def run(_):
            c=TestClient(self.app,base_url='https://api.tolf.is',headers={'Origin':'https://vpn.tolf.is'})
            return c.post('/password/recover',json={'username':'lena-work','password':NEW,'recoveryCode':code}).status_code
        with ThreadPoolExecutor(2) as pool:codes=list(pool.map(run,range(2)))
        self.assertEqual(sorted(codes),[200,401])

    def test_rate_limit_and_restart_persistence(self):
        # Invalid recovery attempts are cheap but still persistently rate limited.
        body={'username':'nobody','password':NEW,'recoveryCode':'invalid'}
        for _ in range(10):self.post('recover',body,401)
        self.post('recover',body,429)
        app=FastAPI()
        # Persistence is in SQLite, not a process-local counter.
        self.assertEqual(self.rows("SELECT count FROM password_attempts WHERE key LIKE 'recover:login:%'"),[(10,)])

    def test_validation_origin_and_delete_cleanup(self):
        for name in ['', 'ab', '../root', 'юзер', 'a'*33]:
            self.post('register',{'username':name,'password':PASS},400)
        for value in ['short','a'*129,'passwordpassword']:
            self.post('register',{'username':'test-user','password':value},400)
        for path in ['register','login','recover']:
            r=self.client.post('/password/'+path,json={'username':'test-user','password':PASS},headers={'Origin':'https://evil.example'})
            self.assertEqual(r.status_code,403)
        self.register()
        with sqlite3.connect(self.db) as con:con.execute('DELETE FROM users')
        self.assertEqual(self.rows('SELECT count(*) FROM account_passwords'),[(0,)])
        self.post('login',{'username':'lena-work','password':PASS},401)

    def test_reset_during_login_cannot_issue_old_session(self):
        code=self.register().json()['recoveryCode'];real=mod.derive
        def interleave(value,salt):
            result=real(value,salt)
            with sqlite3.connect(self.db) as con:con.execute('UPDATE account_passwords SET digest=?',(b'x'*32,))
            return result
        with patch.object(mod,'derive',interleave):self.post('login',{'username':'lena-work','password':PASS},401)

    def test_manage_password_after_passkey_session(self):
        original=self.register().json()['recoveryCode']
        uid=self.client.get('/me').json()['userId']
        old_token=self.client.cookies.get('tolf_session')
        # A Passkey login issues the identical session contract. Use an independent
        # session, without submitting the account password to the management API.
        passkey_token=secrets.token_urlsafe(32)
        with sqlite3.connect(self.db) as con:
            con.execute('INSERT INTO sessions SELECT ?,user_id,created_at,expires_at FROM sessions LIMIT 1',(hashlib.sha256(passkey_token.encode()).digest(),))
            con.execute('INSERT INTO passkeys(credential_id,user_id) VALUES (?,?)',(b'passkey',uid))
        self.client.cookies.clear();self.client.cookies.set('tolf_session',passkey_token)
        metadata=self.client.get('/password/account')
        self.assertEqual(metadata.json(),{'enabled':True,'username':'lena-work'})
        self.assertEqual(metadata.headers['cache-control'],'no-store')
        self.assertNotIn('digest',metadata.text);self.assertNotIn(PASS,metadata.text)
        self.post('set',{'password':NEW,'username':'ignored-rename','userId':'someone-else'})
        self.assertEqual(self.client.get('/me').json()['userId'],uid)
        self.assertEqual(self.rows('SELECT username FROM account_passwords'),[('lena-work',)])
        self.assertEqual(self.rows('SELECT count(*) FROM passkeys'),[(1,)])
        self.assertEqual(self.rows('SELECT recovery_code_hash FROM users'),[(hashlib.sha256(original.encode()).digest(),)])
        self.assertEqual(self.rows('SELECT count(*) FROM sessions'),[(1,)])
        self.post('login',{'username':'lena-work','password':PASS},401)
        self.post('login',{'username':'lena-work','password':NEW})

    def test_add_password_to_passkey_only_account_and_isolation(self):
        self.register('owner-one');uid=self.client.get('/me').json()['userId']
        with sqlite3.connect(self.db) as con:con.execute('DELETE FROM account_passwords WHERE user_id=?',(uid,))
        self.assertEqual(self.client.get('/password/account').json(),{'enabled':False,'username':None})
        self.post('set',{'username':'new-login','password':NEW})
        self.assertEqual(self.rows('SELECT id FROM users'),[(uid,)])
        self.post('login',{'username':'new-login','password':NEW})
        other=TestClient(self.app,base_url='https://api.tolf.is',headers={'Origin':'https://vpn.tolf.is'})
        self.register('owner-two')
        self.post('set',{'password':PASS,'userId':uid})
        self.assertEqual(self.rows('SELECT username FROM account_passwords WHERE user_id=?',(uid,)),[('new-login',)])
        self.assertEqual(other.get('/password/account').status_code,401)
        self.post('set',{'username':'new-login','password':NEW},401,client=other)
        self.post('login',{'username':'new-login','password':NEW})

    def test_revoked_session_cannot_set_password(self):
        self.register();real=mod.derive
        def revoke(value,salt):
            result=real(value,salt)
            with sqlite3.connect(self.db) as con:con.execute('DELETE FROM sessions')
            return result
        with patch.object(mod,'derive',revoke):self.post('set',{'password':NEW},401)
        self.post('login',{'username':'lena-work','password':PASS})

    def test_installer_is_additive_and_idempotent(self):
        spec=importlib.util.spec_from_file_location('installer',ROOT/'setup/password-auth/install-template.py')
        installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
        source='\n'.join('def '+name+'(): pass' for name in ['authenticated_user_id','generate_recovery_code','recovery_code_hash','passkey_register_finish'])+'\n'
        updated=installer.patch(source);self.assertTrue(updated.startswith(source))
        self.assertEqual(installer.patch(updated),updated)
        with self.assertRaises(RuntimeError):installer.patch('x=1')

if __name__=='__main__':unittest.main()
