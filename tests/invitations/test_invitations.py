import contextlib
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
import types
import unittest
from unittest.mock import patch
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'setup/invitations'
FIX = Path(__file__).parent / 'fixtures'

def module(name):
    spec = importlib.util.spec_from_file_location(name, SRC / (name+'.py'))
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

class Invitations(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.riga = module('tolf_invite_riga')
        self.riga.ROOT = self.path/'registry'
        self.riga.CREDS = self.path/'creds'
        self.riga.CREDS.mkdir()
        self.con = self.riga.database()
        self.addCleanup(self.con.close)
        self.account = str(uuid.uuid4())
        self.user('user0')
        self.user('manual')

    def user(self,name):
        p = self.riga.CREDS/('user-'+name+'.conf')
        p.write_text('secrets {\n eap-'+name+' {\n id = '+name+'\n secret = "unchanged-test-secret"\n }\n}\n')
        return p

    def invite(self,name='user0'):
        return self.riga.issue(self.con,name).split('#invite=')[1]

    def test_single_use_idempotent_and_no_credential_changes(self):
        before = {p.name:p.read_bytes() for p in self.riga.CREDS.iterdir()}
        token = self.invite()
        response = self.riga.claim(self.con,self.account,token)
        self.assertTrue(response['protected'])
        self.assertEqual(response,self.riga.claim(self.con,self.account,token))
        with self.assertRaises(self.riga.Rejected):
            self.riga.claim(self.con,str(uuid.uuid4()),token)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.riga.CREDS.iterdir()})
        self.assertNotIn(token,(self.riga.ROOT/'bindings.db').read_bytes().decode(errors='ignore'))

    def test_expiry_and_superseded_invitation(self):
        old = self.invite()
        token = self.invite()
        with self.assertRaises(self.riga.Rejected): self.riga.claim(self.con,self.account,old)
        with self.con: self.con.execute('UPDATE invitations SET expires=0')
        with self.assertRaises(self.riga.Rejected): self.riga.claim(self.con,self.account,token)

    def test_cannot_replace_existing_uuid_credentials(self):
        token = self.invite()
        self.user('user_'+self.account.replace('-',''))
        with self.assertRaises(self.riga.Rejected): self.riga.claim(self.con,self.account,token)
        self.assertEqual(self.con.execute('SELECT count(*) FROM bindings').fetchone()[0],0)

    def test_cannot_link_second_username(self):
        self.riga.claim(self.con,self.account,self.invite())
        with self.assertRaises(self.riga.Rejected): self.riga.claim(self.con,self.account,self.invite('manual'))

    def test_cannot_invite_generated_or_missing_user(self):
        name='user_'+uuid.uuid4().hex
        self.user(name)
        for value in (name,'missing','../user0','user0; echo x'):
            with self.assertRaises(self.riga.Rejected): self.invite(value)

    def claim_remote(self, uid, tok):
        with self.riga.database() as con:
            return self.riga.claim(con,uid,tok)

    def api(self):
        self.api_module = module('tolf_invitations')
        db = str(self.path/'api.db')
        with sqlite3.connect(db) as con:
            con.executescript('CREATE TABLE users(id TEXT PRIMARY KEY); CREATE TABLE vpn_access(user_id TEXT PRIMARY KEY,vpn_username TEXT UNIQUE,created_at TEXT,server TEXT);')
            con.execute('INSERT INTO users VALUES(?)',(self.account,))
        def vpn_record(uid):
            with sqlite3.connect(db) as con: return con.execute('SELECT vpn_username FROM vpn_access WHERE user_id=?',(uid,)).fetchone()
        def authenticate(request):
            if request.headers.get('authorization')!='test': raise HTTPException(401)
            return self.account
        context = dict(DB=db,ORIGIN='https://vpn.tolf.is',authenticated_user_id=authenticate,
            vpn_record=vpn_record,tolf_promos=types.SimpleNamespace(account_operation=lambda *_:contextlib.nullcontext()),
            utc_now=lambda:datetime.now(timezone.utc),utc_iso=lambda dt:dt.isoformat())
        app=FastAPI()
        self.api_module.install(app,context)
        self.client=TestClient(app)
        self.api_module.remote_claim=self.claim_remote
        self.headers={'origin':context['ORIGIN'],'authorization':'test'}
        return db

    def test_api_auth_origin_and_existing_access(self):
        db=self.api()
        token=self.invite()
        for headers,code in (({},403),({'origin':'https://vpn.tolf.is'},401)):
            self.assertEqual(self.client.post('/vpn/invitations/claim',json={'token':token},headers=headers).status_code,code)
        with sqlite3.connect(db) as con: con.execute('INSERT INTO vpn_access VALUES(?,?,?,?)',(self.account,'another','now','riga'))
        self.assertEqual(self.client.post('/vpn/invitations/claim',json={'token':token},headers=self.headers).status_code,409)
        self.assertEqual(self.con.execute('SELECT count(*) FROM bindings').fetchone()[0],0)

    def test_api_lost_response_retry_and_protected_preflight(self):
        db=self.api()
        token=self.invite()
        def lost(uid,tok):
            self.claim_remote(uid,tok)
            raise HTTPException(502,'lost response')
        self.api_module.remote_claim=lost
        self.assertEqual(self.client.post('/vpn/invitations/claim',json={'token':token},headers=self.headers).status_code,502)
        with self.assertRaises(HTTPException): self.api_module.require_ready(self.account)
        self.api_module.remote_claim=self.claim_remote
        for _ in range(2):
            self.assertEqual(self.client.post('/vpn/invitations/claim',json={'token':token},headers=self.headers).status_code,200)
        self.api_module.require_ready(self.account)
        with self.assertRaises(HTTPException): self.api_module.before_account_delete(self.account)
        with sqlite3.connect(db) as con:
            self.assertEqual(con.execute('SELECT vpn_username FROM vpn_access').fetchall(),[('user0',)])

    def test_api_rejected_token_does_not_block_account(self):
        self.api()
        def rejected(*_): raise HTTPException(409,'invalid_invitation')
        self.api_module.remote_claim=rejected
        self.assertEqual(self.client.post('/vpn/invitations/claim',json={'token':'x'*43},headers=self.headers).status_code,409)
        self.api_module.require_ready(self.account)

    def test_concurrent_claims_only_one_wins(self):
        token=self.invite()
        source=(SRC/'tolf_invite_riga.py').read_text()
        source=source.replace("Path('/var/lib/ike-users/web-bindings')", 'Path('+repr(str(self.riga.ROOT))+')')
        source=source.replace("Path('/etc/swanctl/conf.d')", 'Path('+repr(str(self.riga.CREDS))+')')
        source=source.replace("Path('/var/lock/tolf-provision.lock')", 'Path('+repr(str(self.path/'lock'))+')')
        script=self.path/'registry.py';script.write_text(source)
        processes=[subprocess.Popen(['python3',str(script),'claim-existing',str(uuid.uuid4()),token],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
        for proc in processes: proc.communicate(timeout=10)
        self.assertEqual(sorted(proc.returncode for proc in processes),[0,1])
        self.assertEqual(self.con.execute('SELECT count(*) FROM bindings').fetchone()[0],1)

    def test_london_guard_runs_before_windows_deletion(self):
        installer=module('install')
        source = '\n'.join('def '+name+'(): pass' for name in ('vpn_record','authenticated_user_id','utc_iso','utc_now'))
        source += '\ndef provision_on_riga(action, user_id, server="riga", local_id=None):\n    pass\n'
        source += '\ndef account_delete():\n    with lock():\n        tolf_windows.delete_all(user_id)\n        for table in ("windows_devices", "vpn_access", "passkeys", "sessions"):\n            pass\n'
        changed=installer.london_source(source)
        self.assertLess(changed.index('tolf_invitations.before_account_delete'),changed.index('tolf_windows.delete_all'))
        with self.assertRaises(RuntimeError): installer.london_source(changed)

    def test_patched_provisioner_reads_manual_password_and_blocks_delete(self):
        installer=module('install')
        root,wrapper=installer.riga_sources((FIX/'provision-root.sh').read_text(),(FIX/'provision-ssh.sh').read_text())
        for text in (root,wrapper):
            subprocess.run(['bash','-n'],input=text,text=True,check=True)
        fakehelper=self.path/'helper'
        fakehelper.write_text('#!/bin/sh\nprintf "user0\\n"\n')
        fakehelper.chmod(0o700)
        root=root.replace('/usr/local/sbin/tolf-invite',str(fakehelper)).replace('/etc/swanctl/conf.d',str(self.riga.CREDS)).replace('/var/lock/tolf-provision.lock',str(self.path/'lock')).replace('/var/lib/ike-users',str(self.path/'ike-users'))
        script=self.path/'root.sh';script.write_text(root)
        result=subprocess.run(['bash',str(script),'profile',self.account,'riga','sr'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        data=json.loads(result.stdout)
        self.assertEqual(data['username'],'user0')
        self.assertEqual(data['password'],'unchanged-test-secret')
        for action in ('delete','revoke-moscow'):
            result=subprocess.run(['bash',str(script),action,self.account],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('protected VPN user',result.stdout)
        self.assertTrue((self.riga.CREDS/'user-user0.conf').exists())
        with self.assertRaises(RuntimeError): installer.riga_sources(root,wrapper)

if __name__=='__main__': unittest.main()
