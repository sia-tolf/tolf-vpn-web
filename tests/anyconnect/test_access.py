from contextlib import contextmanager
import importlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid
from urllib.parse import urlparse,parse_qs
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs12
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'setup/anyconnect'))
certificates=importlib.import_module('tolf_oc_certificates')
api=importlib.import_module('tolf_anyconnect')


class Promos:
    def __init__(self): self.lock=threading.RLock()
    @contextmanager
    def account_operation(self,db,user):
        with self.lock:
            with sqlite3.connect(db) as con:
                if not con.execute('SELECT 1 FROM users WHERE id=?',(user,)).fetchone():
                    raise HTTPException(404,'Account not found')
            yield


class PersonalAccess(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.directory=Path(self.temp.name)
        self.db=self.directory/'tolf.db'
        with sqlite3.connect(self.db) as con:
            con.execute('CREATE TABLE users(id TEXT PRIMARY KEY)')
            con.executemany('INSERT INTO users VALUES (?)',[('owner',),('other',)])
        self.fingerprint=certificates.initialize(self.directory/'anyconnect')
        self.gate=self.directory/'anyconnect/activation.json'
        self.gate.write_text(json.dumps({'enabled':True,'caSha256':self.fingerprint}))
        self.commands=[];self.modes={};self.sessions=set();self.fail_set=False;self.fail_remove=False
        self.bad_trust=False
        def remote(command):
            self.commands.append(command)
            parts=command.split()
            if parts[0] in {'tolf-oc-node-health','tolf-oc-crl-sync'}:
                return {'status':'ok','version':1,'caSha256':'wrong' if self.bad_trust else self.fingerprint,'deviceRouting':True,'issuance':False}
            if parts[0]=='tolf-oc-device':
                if self.fail_set: raise ValueError('Node failed')
                self.modes[parts[1]]=parts[2]
                return {'status':'ok','username':parts[1],'mode':parts[2]}
            if parts[0]=='tolf-oc-device-remove':
                if self.fail_remove: raise ValueError('Node failed')
                self.modes.pop(parts[1],None);self.sessions.discard(parts[1])
                return {'status':'ok','username':parts[1],'removed':True}
            if parts[0]=='tolf-oc-session':
                return {'status':'ok','username':parts[1],'connected':parts[1] in self.sessions}
            raise ValueError('Unexpected command')
        def authenticate(request):
            user=request.cookies.get('test-session')
            if user not in {'owner','other'}:raise HTTPException(401,'Not authenticated')
            return user
        self.app=FastAPI()
        api.install(self.app,{'DB':str(self.db),'ORIGIN':'https://vpn.tolf.is','authenticated_user_id':authenticate,
                              'tolf_promos':Promos(),'OC_REMOTE':remote})
        self.client=TestClient(self.app)
        self.client.cookies.set('test-session','owner')
        self.headers={'Origin':'https://vpn.tolf.is'}

    def tearDown(self):self.temp.cleanup()
    def create(self,request_id=None):
        return self.client.post('/oc/access/devices',headers=self.headers,json={'requestId':request_id or str(uuid.uuid4()),'label':'iPad'})
    def grant(self,device):
        return self.client.post('/oc/access/devices/'+device['id']+'/import',headers=self.headers).json()

    def setup_link(self,device):
        result=self.client.post('/oc/access/devices/'+device['id']+'/setup-link',headers=self.headers)
        self.assertEqual(result.status_code,200,result.text)
        return urlparse(result.json()['setupUrl']).fragment

    def test_guest_setup_metadata_does_not_consume_and_claim_needs_no_login(self):
        device=self.create().json()['device'];token=self.setup_link(device)
        self.client.cookies.clear()
        path='/oc/access/setup/'+token
        for _ in range(2):
            info=self.client.get(path)
            self.assertEqual(info.status_code,200,info.text)
            self.assertEqual(info.json()['label'],'iPad')
            self.assertNotIn('password',info.json())
            self.assertNotIn('certificateUrl',info.json())
        self.assertEqual(self.client.post(path+'/claim').status_code,403)
        result=self.client.post(path+'/claim',headers=self.headers)
        self.assertEqual(result.status_code,200,result.text)
        grant=result.json()
        self.assertEqual(self.client.get(path).status_code,410)
        self.assertEqual(self.client.post(path+'/claim',headers=self.headers).status_code,410)
        response=self.client.get(urlparse(grant['certificateUrl']).path)
        self.assertEqual(response.status_code,200)
        _,cert,_=pkcs12.load_key_and_certificates(response.content,grant['password'].encode())
        self.assertEqual(cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value,device['username'])
        self.assertEqual(self.client.get(urlparse(grant['certificateUrl']).path).status_code,410)
        self.assertEqual(self.client.get('/oc/access/devices/'+device['id']+'/policy').status_code,401)

    def test_setup_links_require_owner_and_expire_rotate_or_revoke(self):
        device=self.create().json()['device'];token=self.setup_link(device)
        self.client.cookies.set('test-session','other')
        self.assertEqual(self.client.post('/oc/access/devices/'+device['id']+'/setup-link',headers=self.headers).status_code,404)
        self.client.cookies.set('test-session','owner')
        replacement=self.setup_link(device)
        self.assertEqual(self.client.get('/oc/access/setup/'+token).status_code,410)
        with sqlite3.connect(self.db) as con:
            con.execute("UPDATE oc_setup_links SET expires_at='2000-01-01T00:00:00+00:00'")
        self.assertEqual(self.client.post('/oc/access/setup/'+replacement+'/claim',headers=self.headers).status_code,410)
        token=self.setup_link(device)
        self.client.post('/oc/access/devices/'+device['id']+'/revoke',headers=self.headers)
        self.assertEqual(self.client.get('/oc/access/setup/'+token).status_code,410)

    def test_setup_link_is_invalid_after_account_deletion(self):
        device=self.create().json()['device'];token=self.setup_link(device)
        with sqlite3.connect(self.db) as con:con.execute("DELETE FROM users WHERE id='owner'")
        self.assertEqual(self.client.post('/oc/access/setup/'+token+'/claim',headers=self.headers).status_code,410)

    def test_setup_claim_is_atomic(self):
        device=self.create().json()['device'];token=self.setup_link(device)
        statuses=[]
        def claim():statuses.append(self.client.post('/oc/access/setup/'+token+'/claim',headers=self.headers).status_code)
        threads=[threading.Thread(target=claim) for _ in range(2)]
        for thread in threads:thread.start()
        for thread in threads:thread.join()
        self.assertEqual(sorted(statuses),[200,410])

    def test_create_is_idempotent_and_contains_no_private_material(self):
        key=str(uuid.uuid4());one=self.create(key);two=self.create(key)
        self.assertEqual(one.status_code,200,one.text)
        self.assertEqual(one.json(),two.json())
        device=one.json()['device']
        self.assertRegex(device['username'],r'^tolf-oc-[0-9a-f]{32}$')
        self.assertEqual(device['state'],'active')
        self.assertNotIn('encrypted_key',device)
        self.assertEqual(len([c for c in self.commands if c.startswith('tolf-oc-device ')]),1)

    def test_create_recovers_pending_after_node_failure(self):
        key=str(uuid.uuid4());self.fail_set=True
        self.assertEqual(self.create(key).status_code,503)
        with sqlite3.connect(self.db) as con:
            old=con.execute('SELECT id,serial,state FROM oc_devices').fetchone()
        self.assertEqual(old[2],'pending');self.fail_set=False
        result=self.create(key)
        self.assertEqual(result.status_code,200,result.text)
        with sqlite3.connect(self.db) as con:
            current=con.execute('SELECT id,serial,state FROM oc_devices').fetchone()
        self.assertEqual(old[:2],current[:2]);self.assertEqual(current[2],'active')

    def test_other_account_cannot_import_route_check_or_revoke_device(self):
        device=self.create().json()['device'];self.client.cookies.set('test-session','other')
        prefix='/oc/access/devices/'+device['id']
        self.assertEqual(self.client.get('/oc/access/devices').json()['devices'],[])
        for suffix in ('/policy','/session'):
            self.assertEqual(self.client.get(prefix+suffix).status_code,404)
        for suffix in ('/import','/revoke'):
            self.assertEqual(self.client.post(prefix+suffix,headers=self.headers).status_code,404)
        self.assertEqual(self.client.post(prefix+'/policy',headers=self.headers,json={'mode':'ru'}).status_code,404)

    def test_bundle_single_use_and_uri_encodings(self):
        device=self.create().json()['device'];grant=self.grant(device)
        path=urlparse(grant['certificateUrl']).path
        self.assertEqual(self.client.head(path).status_code,200)
        response=self.client.get(path)
        self.assertEqual(response.status_code,200,response.text)
        key,cert,chain=pkcs12.load_key_and_certificates(response.content,grant['password'].encode())
        self.assertEqual(cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value,device['username'])
        self.assertEqual(key.public_key().public_numbers(),cert.public_key().public_numbers())
        self.assertEqual(self.client.get(path).status_code,410)
        import_values=parse_qs(urlparse(grant['importUri']).query)
        self.assertEqual(import_values['uri'],[grant['certificateUrl']])
        connection=parse_qs(urlparse(grant['connectionUri']).query)
        self.assertEqual(connection['certcommonname'],[device['username']])
        self.assertEqual(connection['host'],['oc.tolf.is:4443'])
        self.assertNotIn(grant['password'],grant['importUri'])
        self.assertLessEqual(len(grant['connectionName']),24)

    def test_import_expiry_and_revocation_invalidate_tokens(self):
        device=self.create().json()['device'];grant=self.grant(device)
        with sqlite3.connect(self.db) as con:
            con.execute("UPDATE oc_import_grants SET expires_at='2000-01-01T00:00:00+00:00'")
        self.assertEqual(self.client.get(urlparse(grant['certificateUrl']).path).status_code,410)
        grant=self.grant(device)
        self.sessions.add(device['username'])
        response=self.client.post('/oc/access/devices/'+device['id']+'/revoke',headers=self.headers)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['device']['state'],'revoked')
        self.assertNotIn(device['username'],self.sessions)
        self.assertEqual(self.client.get(urlparse(grant['certificateUrl']).path).status_code,410)
        with sqlite3.connect(self.db) as con:
            serial=con.execute('SELECT serial FROM oc_devices').fetchone()[0]
        crl=x509.load_pem_x509_crl(self.client.get('/oc/access/crl.pem').content)
        self.assertIsNotNone(crl.get_revoked_certificate_by_serial_number(int(serial,16)))

    def test_revocation_remains_pending_until_node_acknowledges(self):
        device=self.create().json()['device'];self.fail_remove=True
        prefix='/oc/access/devices/'+device['id']
        response=self.client.post(prefix+'/revoke',headers=self.headers)
        self.assertEqual(response.status_code,202,response.text)
        self.assertEqual(response.json()['device']['state'],'revoking')
        self.assertEqual(self.client.post(prefix+'/import',headers=self.headers).status_code,409)
        self.fail_remove=False
        self.assertEqual(self.client.post(prefix+'/revoke',headers=self.headers).json()['device']['state'],'revoked')

    def test_mode_and_session_are_personal(self):
        one=self.create().json()['device'];two=self.create().json()['device']
        self.sessions.add(one['username'])
        prefix='/oc/access/devices/'+one['id']
        self.assertTrue(self.client.get(prefix+'/session').json()['connected'])
        self.assertFalse(self.client.get('/oc/access/devices/'+two['id']+'/session').json()['connected'])
        self.assertEqual(self.client.post(prefix+'/policy',headers=self.headers,json={'mode':'yt'}).status_code,200)
        self.assertEqual(self.modes[one['username']],'yt');self.assertEqual(self.modes[two['username']],'auto')

    def test_activation_and_origin_must_match(self):
        self.assertEqual(self.client.post('/oc/access/devices',json={}).status_code,403)
        self.gate.write_text(json.dumps({'enabled':True,'caSha256':'wrong'}))
        self.assertFalse(self.client.get('/oc/access/capabilities').json()['issuance'])
        self.assertEqual(self.create().status_code,503)
        self.gate.write_text(json.dumps({'enabled':True,'caSha256':self.fingerprint}))
        self.bad_trust=True
        self.assertEqual(self.create().status_code,503)

    def assert_background_revoked(self,device):
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            with sqlite3.connect(self.db) as con:
                state=con.execute('SELECT state FROM oc_devices WHERE id=?',(device['id'],)).fetchone()[0]
            if state=='revoked':break
            time.sleep(.02)
        self.assertEqual(state,'revoked')
        self.assertNotIn(device['username'],self.sessions)
        self.assertNotIn(device['username'],self.modes)

    def test_background_disconnects_deleted_account(self):
        with patch.object(api,'RECONCILE_INTERVAL',.02), TestClient(self.app):
            device=self.create().json()['device']
            grant=self.grant(device);self.sessions.add(device['username'])
            with sqlite3.connect(self.db) as con:
                con.execute("DELETE FROM users WHERE id='owner'")
            self.assert_background_revoked(device)
            self.assertEqual(self.client.get(urlparse(grant['certificateUrl']).path).status_code,410)

    def test_background_disconnects_expired_certificate(self):
        with patch.object(api,'RECONCILE_INTERVAL',.02), TestClient(self.app):
            device=self.create().json()['device'];self.sessions.add(device['username'])
            with sqlite3.connect(self.db) as con:
                con.execute("UPDATE oc_devices SET expires_at='2000-01-01T00:00:00+00:00'")
            self.assert_background_revoked(device)


if __name__=='__main__':unittest.main()
