import contextlib
import json
from pathlib import Path
import sys
import types
import uuid
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'setup/windows'))
import tolf_windows as w
import tolf_windows_certificates as certificates
import tolf_windows_ca as ca

def test_certificate_identity_and_encrypted_storage(tmp_path):
    directory = tmp_path/'ca'
    ca.initialize(directory)
    authority = ca.Authority(directory)
    device = str(uuid.uuid4())
    issued = authority.issue(device)
    certificate = x509.load_pem_x509_certificate(issued['certificate'])
    expected = 'tolf-win-'+uuid.UUID(device).hex+'.tolf.is'
    assert certificate.subject.rfc4514_string() == 'CN='+expected
    assert certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName) == [expected]
    assert b'ENCRYPTED PRIVATE KEY' in issued['encrypted_key']
    with pytest.raises(TypeError): serialization.load_pem_private_key(issued['encrypted_key'], None)
    pfx, password = authority.bundle(issued)
    key, cert, chain = pkcs12.load_key_and_certificates(pfx, password.encode())
    assert key.public_key().public_numbers() == cert.public_key().public_numbers()
    assert chain[0].subject == authority.cert.subject
    assert ca.initialize(directory) == authority.fingerprint

def test_certificate_api_lifecycle_owner_retry_revoke(tmp_path, monkeypatch):
    monkeypatch.setattr(certificates, 'CA', tmp_path/'ca')
    monkeypatch.setattr(certificates, 'ROOT', tmp_path/'certificates')
    ca.initialize(certificates.CA)
    monkeypatch.setattr(w.ppkg,'available',lambda:True)
    monkeypatch.setattr(w.ppkg,'build',lambda row,*args:b'MSWIM_TEST_CERTIFICATE_PACKAGE')
    profiles_dir=tmp_path/'profiles';profiles_dir.mkdir()
    calls=[]; fail_remove=[False]
    def rpc(action,row,data):
        calls.append((action,row['id'],data))
        assert 'PRIVATE KEY' not in json.dumps(data)
        if action=='remove' and fail_remove[0]: raise HTTPException(503,'node unavailable')
        return {'status':'ok','deviceId':row['id'],'server':row['server'],'localId':row['local_id']}
    def reject_password(*args): raise AssertionError('Certificate devices must not provision passwords')
    def write(path,data): path.write_bytes(data);path.chmod(0o600)
    context={'DB':str(tmp_path/'accounts.db'),'authenticated_user_id':lambda request:request.headers['x-user'],
             'windows_certificate_rpc':rpc,'provision_on_riga':lambda *args: {'status':'ok'} if args[0]=='revoke-moscow' else reject_password(*args),
             'remove_provisioned_vpn':reject_password,
             'tolf_profiles':types.SimpleNamespace(PROFILE_DIR=profiles_dir,initialize=lambda:None,_atomic_write=write),
             'tolf_promos':types.SimpleNamespace(account_operation=lambda *args:contextlib.nullcontext())}
    app=FastAPI();w.install(app,context)
    owner=str(uuid.uuid4());h={'x-user':owner};other={'x-user':str(uuid.uuid4())}
    with TestClient(app) as client:
        payload={'requestId':str(uuid.uuid4()),'name':'Test <PC>','server':'riga','localId':'sr','packageFormat':'ppkg','language':'ru'}
        response=client.post('/windows/devices',headers=h,json=payload)
        assert response.status_code==200,response.text
        result=response.json();device=result['device']['id']
        assert result['device']['authentication']=='certificate'
        url=result['profileUrl'].replace('https://api.tolf.is','')
        page=client.get(url)
        assert page.status_code==200 and 'Логин и пароль не требуются' in page.text
        assert 'files:[packageFile]' in page.text
        download=client.get(url+'/download')
        assert download.content==b'MSWIM_TEST_CERTIFICATE_PACKAGE'
        assert '.ppkg' in download.headers['content-disposition']
        assert client.post(url+'/settings').status_code==409
        assert client.post('/windows/devices/'+device+'/password',headers=h).status_code==409
        serial=certificates.record(device)['serial']
        retry=client.post('/windows/devices',headers=h,json=payload)
        assert retry.status_code==200 and retry.json()['device']['id']==device
        assert certificates.record(device)['serial']==serial
        assert client.post('/windows/devices/'+device+'/profile',headers=other,json={'packageFormat':'ppkg'}).status_code==404
        assert client.post('/windows/devices/'+device+'/delete',headers=other,json={}).status_code==404
        fail_remove[0]=True
        assert client.post('/windows/devices/'+device+'/delete',headers=h,json={}).status_code==503
        assert client.get(url+'/download').status_code==404
        fail_remove[0]=False
        assert client.post('/windows/devices/'+device+'/delete',headers=h,json={}).status_code==200
        assert client.get(url+'/download').status_code==404
        assert json.loads(certificates.path_for(device).read_text())['state']=='revoked'
        assert 'encrypted_key' not in json.loads(certificates.path_for(device).read_text())
        assert client.post('/windows/devices/'+device+'/delete',headers=h,json={}).status_code==200
