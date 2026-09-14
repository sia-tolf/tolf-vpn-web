import importlib.util
import sqlite3
import uuid
from pathlib import Path
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('admin_module',ROOT/'setup/admin/tolf_admin.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
spec=importlib.util.spec_from_file_location('installer',ROOT/'setup/admin/install-template.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)

@pytest.fixture
def database(tmp_path):
    path=str(tmp_path/'db');one=str(uuid.uuid4());two=str(uuid.uuid4())
    with sqlite3.connect(path) as db:
        db.executescript('''
CREATE TABLE users(id TEXT PRIMARY KEY,created_at TEXT,recovery_code_hash BLOB);
CREATE TABLE managed_users(number INTEGER PRIMARY KEY,account_id TEXT,vpn_username TEXT,created_at TEXT,vpn_created_at TEXT,source TEXT,vpn_active INTEGER,deleted_at TEXT);
CREATE TABLE vpn_access(user_id TEXT,vpn_username TEXT,created_at TEXT,server TEXT);
CREATE TABLE passkeys(user_id TEXT,name TEXT,created_at TEXT,public_key BLOB);
CREATE TABLE vpn_imports(user_id TEXT,protected INTEGER);
CREATE TABLE windows_devices(id TEXT,user_id TEXT,name TEXT,username TEXT,state TEXT,created_at TEXT);
CREATE TABLE windows_device_nodes(device_id TEXT,server TEXT);
CREATE TABLE sessions(token_hash BLOB,user_id TEXT);
''')
        for i,user in enumerate((one,two),1):
            db.execute('INSERT INTO users VALUES(?,?,?)',(user,'2026-09-14T00:00:00+00:00',b'SECRET_RECOVERY'))
            db.execute('INSERT INTO managed_users VALUES(?,?,?,?,?,?,?,?)',(i,user,'user_'+str(i),'2026-09-14',None,'website',1,None))
            db.execute('INSERT INTO passkeys VALUES(?,?,?,?)',(user,'iPad '+str(i),'2026-09-14',b'SECRET_PUBLIC_KEY'))
            db.execute('INSERT INTO vpn_access VALUES(?,?,?,?)',(user,'user_'+str(i),'2026-09-14','riga'))
        db.execute('INSERT INTO managed_users VALUES(3,NULL,?,NULL,NULL,?,1,NULL)',('manual','manual'))
        db.execute('INSERT INTO windows_devices VALUES(?,?,?,?,?,?)',(str(uuid.uuid4()),two,'Office <script>','user_device','active','2026-09-14'))
        db.execute('INSERT INTO sessions VALUES(?,?)',(b'SECRET_TOKEN',one))
    return path,one,two


def test_auth_inventory_and_revocation(database):
    path,one,two=database
    app=FastAPI()
    def auth(request):
        user=request.headers.get('x-test-user')
        if not user:raise HTTPException(401,'not authenticated')
        return user
    a.install(app,{'DB':path,'authenticated_user_id':auth})
    h={'x-test-user':one};other={'x-test-user':two}
    with TestClient(app) as c:
        assert c.get('/admin/capabilities').json()['disconnect'] is False
        assert c.get('/admin/me').status_code==401
        assert c.get('/admin/me',headers=h).json()=={'isAdmin':False,'number':1,'features':{'sessions':True,'testDisconnect':True,'testAccess':True}}
        for endpoint in ('users','users/'+two,'registry','audit','sessions'):
            assert c.get('/admin/'+endpoint).status_code==401
            assert c.get('/admin/'+endpoint,headers=h).status_code==403
        a.root_grant(path,1);a.root_grant(path,1)
        assert c.get('/admin/me',headers=h).json()['isAdmin'] is True
        users=c.get('/admin/users',headers=h)
        assert users.json()['total']==2
        assert users.json()['source']=='account_database'
        assert 'no-store' in users.headers['cache-control']
        assert c.get('/admin/users?limit=1',headers=h).json()['users'].__len__()==1
        assert c.get('/admin/users?q=Office',headers=h).json()['users'][0]['id']==two
        assert c.get('/admin/users',params={'q':"' OR 1=1 --"},headers=h).json()['total']==0
        assert c.get('/admin/users?limit=101',headers=h).status_code==400
        assert c.get('/admin/users?offset=-1',headers=h).status_code==400
        detail=c.get('/admin/users/'+two,headers=h)
        assert detail.json()['devices'][0]['server']=='riga' # legacy location default
        assert detail.json()['devices'][0]['name']=='Office <script>'
        assert detail.json()['passkeyNames']==['iPad 2']
        assert len(c.get('/admin/registry',headers=h).json()['records'])==3
        assert len(c.get('/admin/audit',headers=h).json()['events'])==1
        for endpoint in ('users','users/'+two,'registry','audit','sessions'):
            result=c.get('/admin/'+endpoint,headers=h)
            assert 'SECRET_' not in result.text
            assert c.get('/admin/'+endpoint,headers=other).status_code==403
        assert c.post('/admin/users/'+two+'/delete',headers=h).status_code==404
        a.root_revoke(path,1)
        assert c.get('/admin/users',headers=h).status_code==403
        assert c.get('/admin/me',headers=h).json()['isAdmin'] is False
        with sqlite3.connect(path) as db:
            assert db.execute('SELECT count(*) FROM users').fetchone()[0]==2
            assert db.execute('SELECT count(*) FROM vpn_access').fetchone()[0]==2
            assert db.execute('SELECT count(*) FROM sessions').fetchone()[0]==1


def test_invalid_role_target(database):
    path,one,two=database
    with pytest.raises(ValueError):a.root_grant(path,3) # unlinked VPN user is not an account
    with pytest.raises(ValueError):a.root_grant(path,999)
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM admin_roles').fetchone()[0]==0


def test_installer_preserves_existing_source():
    source='app = object()\nDB = "db"\ndef authenticated_user_id(request):\n    return "id"\n\nif __name__ == "__main__":\n    run()\n'
    result=installer.patch(source)
    assert result.index('tolf_admin.install')<result.index('if __name__')
    assert result.replace('\n'+installer.MARKER+'\nimport tolf_admin\ntolf_admin.install(app, globals())\n\n','')==source
    assert installer.patch(result)==result
    with pytest.raises(RuntimeError):installer.patch('app = object()')


def test_live_sessions_access_mapping_and_partial_failure(database, monkeypatch):
    path,one,two=database
    app=FastAPI()
    def auth(request):
        user=request.headers.get('x-test-user')
        if not user:raise HTTPException(401,'not authenticated')
        return user
    a.install(app,{'DB':path,'authenticated_user_id':auth})
    calls=[]
    def query(node):
        calls.append(node)
        if node=='riga':return {'node':node,'status':'error','error':'node_unavailable'}
        return {'node':node,'status':'ok','observedAt':'2026-09-14T14:44:07+00:00','sessions':[
            {'identity':'user_2'}, {'identity':'user_device'}, {'identity':'manual'}, {'identity':'192.168.1.1'}]}
    monkeypatch.setattr(a,'query_node',query)
    with TestClient(app) as c:
        assert c.get('/admin/sessions').status_code==401
        assert c.get('/admin/sessions',headers={'x-test-user':two}).status_code==403
        assert calls==[]
        a.root_grant(path,1)
        result=c.get('/admin/sessions',headers={'x-test-user':one})
        assert result.status_code==200 and 'no-store' in result.headers['cache-control']
        riga,moscow=result.json()['nodes']
        assert riga['status']=='error' and 'sessions' not in riga
        assert moscow['sessions'][0]['account']=={'accountId':two,'number':2}
        assert moscow['sessions'][1]['account']=={'accountId':two,'number':2}
        assert moscow['sessions'][2]['account']=={'accountId':None,'number':3}
        assert moscow['sessions'][3]['account'] is None
        assert a.SESSION_POLL.acquire(blocking=False)
        try:assert c.get('/admin/sessions',headers={'x-test-user':one}).status_code==429
        finally:a.SESSION_POLL.release()
        def revoke_query(node):
            if node=='riga':a.root_revoke(path,1)
            return {'node':node,'status':'ok','sessions':[]}
        monkeypatch.setattr(a,'query_node',revoke_query)
        assert c.get('/admin/sessions',headers={'x-test-user':one}).status_code==403


def test_node_transport_validation(monkeypatch):
    import json
    a.CTX={'RIGA_KNOWN_HOSTS':'known','RIGA_KEY':'key','RIGA_USER':'tolfprov','RIGA_HOST':'riga'}
    body={'status':'ok','version':'1.0.0','node':'moscow','observedAt':'2026-09-14T14:44:07+00:00','sessions':[]}
    class Reply:
        returncode=0
        @property
        def stdout(self):return json.dumps(body)
    commands=[]
    def run(command,**kwargs):
        commands.append(command)
        return Reply()
    monkeypatch.setattr(a.subprocess,'run',run)
    assert a.query_node('moscow')['sessions']==[]
    assert commands[-1][-1]=='admin-sessions moscow'
    assert 'StrictHostKeyChecking=yes' in commands[-1]
    body['sessions']=[dict(id=5441,establishedSeconds=518,bytesIn=1,bytesOut=2,identity='user_1',identitySource='remote-id',virtualAddresses=[],password='DO_NOT_RETURN')]
    result=a.query_node('moscow')
    assert result['status']=='ok' and 'password' not in result['sessions'][0]
    body['sessions'][0]['id']=True
    assert a.query_node('moscow')['status']=='error'
    body['sessions']=[];body['node']='riga'
    assert a.query_node('moscow')['status']=='error'
    with pytest.raises(ValueError):a.query_node('moscow;id')
    def timeout(*args,**kwargs):raise a.subprocess.TimeoutExpired('ssh',40)
    monkeypatch.setattr(a.subprocess,'run',timeout)
    value=a.query_node('moscow')
    assert value['status']=='error' and 'sessions' not in value

@pytest.fixture
def control_client(database, monkeypatch):
    path,one,two=database
    with sqlite3.connect(path) as con:
        con.execute('INSERT INTO users VALUES(?,?,?)',(a.TEST_ACCOUNT,'2026-09-14',None))
        con.execute('INSERT INTO managed_users VALUES(?,?,?,?,?,?,?,?)',(26,a.TEST_ACCOUNT,a.TEST_USERNAME,'2026-09-14',None,'site',1,None))
    app=FastAPI()
    def auth(request):
        user=request.headers.get('x-test-user')
        if not user:raise HTTPException(401)
        return user
    a.install(app,{'DB':path,'authenticated_user_id':auth})
    a.root_grant(path,1)
    calls=[]
    selection={'uniqueid':'5448','initiator-spi':'33c90b2d7d2b4919','responder-spi':'c13a2693c6783e0e'}
    def remote(node, selected=None):
        calls.append((node,selected))
        if selected is None:return {'status':'ok','sessions':[selection.copy()]}
        return {'status':'ok','reconnected':False}
    monkeypatch.setattr(a,'control_call',remote)
    with TestClient(app) as client:
        yield client,{'x-test-user':one,'origin':'https://vpn.tolf.is'},calls,path,one,two,selection


def test_control_auth_csrf_and_unrelated_session(control_client):
    c,h,calls,path,one,two,selection=control_client
    body={'node':'moscow','id':5448}
    for headers,code in [({},401),({'x-test-user':two,'origin':h['origin']},403),({'x-test-user':one},403),({**h,'origin':'https://evil.example'},403)]:
        assert c.post('/admin/disconnect/prepare',json=body,headers=headers).status_code==code
        assert c.post('/admin/disconnect',json={'ticket':'A'*43},headers=headers).status_code==code
    assert not calls
    assert c.post('/admin/disconnect/prepare',json={'node':'moscow;id','id':5448},headers=h).status_code==400
    assert c.post('/admin/disconnect/prepare',json={'node':'moscow','id':123},headers=h).status_code==409
    assert all(selected is None for _,selected in calls)


def test_control_ticket_single_use_and_audit(control_client):
    c,h,calls,path,one,two,selection=control_client
    result=c.post('/admin/disconnect/prepare',json={'node':'moscow','id':5448},headers=h)
    assert result.status_code==200 and 'no-store' in result.headers['cache-control']
    ticket=result.json()['ticket']
    for _ in range(2):
        result=c.post('/admin/disconnect',json={'ticket':ticket},headers=h)
        assert result.json()=={'status':'ok','reconnected':False}
    assert calls==[('moscow',None),('moscow',selection)]
    events=c.get('/admin/audit',headers=h).json()['events']
    assert events[0]['action']=='session.disconnect.ok'
    assert events[1]['action']=='session.disconnect.requested'
    assert ticket not in str(events)
    assert 'Test #26 / moscow / IKE #5448'==events[0]['target']


def test_control_expired_stolen_ticket_and_revocation(control_client):
    c,h,calls,path,one,two,selection=control_client
    a.root_grant(path,2)
    ticket=c.post('/admin/disconnect/prepare',json={'node':'moscow','id':5448},headers=h).json()['ticket']
    assert c.post('/admin/disconnect',json={'ticket':ticket},headers={**h,'x-test-user':two}).status_code==409
    with sqlite3.connect(path) as con:con.execute('UPDATE admin_disconnect_tickets SET expires=0')
    assert c.post('/admin/disconnect',json={'ticket':ticket},headers=h).status_code==409
    a.root_revoke(path,1)
    assert c.post('/admin/disconnect',json={'ticket':ticket},headers=h).status_code==403
    assert all(selected is None for _,selected in calls)


def test_control_unknown_never_retried(control_client,monkeypatch):
    c,h,calls,path,one,two,selection=control_client
    ticket=c.post('/admin/disconnect/prepare',json={'node':'moscow','id':5448},headers=h).json()['ticket']
    attempts=[]
    def unknown(*args):
        attempts.append(args)
        return {'status':'unknown'}
    monkeypatch.setattr(a,'control_call',unknown)
    for _ in range(2):assert c.post('/admin/disconnect',json={'ticket':ticket},headers=h).json()['status']=='unknown'
    assert len(attempts)==1


def test_control_rechecks_role_after_prepare(control_client,monkeypatch):
    c,h,calls,path,one,two,selection=control_client
    def remote(*args):
        a.root_revoke(path,1)
        return {'status':'ok','sessions':[selection]}
    monkeypatch.setattr(a,'control_call',remote)
    assert c.post('/admin/disconnect/prepare',json={'node':'moscow','id':5448},headers=h).status_code==403
    with sqlite3.connect(path) as con:assert con.execute('SELECT count(*) FROM admin_disconnect_tickets').fetchone()[0]==0


def test_control_wire_command_and_unknown(monkeypatch):
    import json
    from types import SimpleNamespace
    a.CTX={'RIGA_KNOWN_HOSTS':'known','RIGA_KEY':'key','RIGA_USER':'tolfprov','RIGA_HOST':'riga'}
    selection={'uniqueid':'5448','initiator-spi':'33c90b2d7d2b4919','responder-spi':'c13a2693c6783e0e'}
    commands=[]
    def run(command,**kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0,stdout=json.dumps({'status':'ok','node':'moscow','accountNumber':26,'disconnected':'5448','reconnected':True}))
    monkeypatch.setattr(a.subprocess,'run',run)
    assert a.control_call('moscow',selection)=={'status':'ok','reconnected':True}
    assert commands[-1][-1]=='admin-test-disconnect moscow 5448 33c90b2d7d2b4919 c13a2693c6783e0e'
    assert 'StrictHostKeyChecking=yes' in commands[-1]
    with pytest.raises(ValueError):a.control_call('moscow',{**selection,'uniqueid':'5448; id'})
    assert len(commands)==1
    def timeout(*args,**kwargs):raise a.subprocess.TimeoutExpired('ssh',40)
    monkeypatch.setattr(a.subprocess,'run',timeout)
    assert a.control_call('moscow',selection)=={'status':'unknown'}


def test_access_auth_validation_and_audit(control_client,monkeypatch):
    c,h,calls,path,one,two,selection=control_client
    attempts=[]
    def access(action,revision=None):
        attempts.append((action,revision))
        return {'status':'ok','state':'suspended' if action=='suspend' else 'active','revision':'b'*32,'accountNumber':26}
    monkeypatch.setattr(a,'access_call',access)
    assert c.get('/admin/test-access').status_code==401
    assert c.get('/admin/test-access',headers={'x-test-user':two}).status_code==403
    for headers in ({'x-test-user':one},{**h,'origin':'https://evil.example'},{**h,'x-test-user':two}):
        assert c.post('/admin/test-access',json={'action':'suspend','revision':'a'*32},headers=headers).status_code==403
    assert not attempts
    for body in ({'action':'delete','revision':'a'*32},{'action':'resume','revision':'bad'},{'action':'suspend','revision':'a'*32,'account':11}):
        assert c.post('/admin/test-access',json=body,headers=h).status_code==400
    assert not attempts
    assert c.get('/admin/test-access',headers=h).json()['state']=='active'
    assert c.post('/admin/test-access',json={'action':'suspend','revision':'a'*32},headers=h).json()['state']=='suspended'
    assert c.post('/admin/test-access',json={'action':'resume','revision':'b'*32},headers=h).json()['state']=='active'
    assert attempts==[('status',None),('suspend','a'*32),('resume','b'*32)]
    audit=c.get('/admin/audit',headers=h).json()['events']
    assert audit[0]['action']=='access.resume.ok'
    assert audit[2]['action']=='access.suspend.ok'
    assert audit[0]['target']=='Test #26 / riga+moscow'


def test_access_partial_response_and_revocation(control_client,monkeypatch):
    c,h,calls,path,one,two,selection=control_client
    monkeypatch.setattr(a,'access_call',lambda *args:{'status':'unknown'})
    assert c.post('/admin/test-access',json={'action':'suspend','revision':'a'*32},headers=h).json()=={'status':'unknown'}
    a.root_revoke(path,1)
    assert c.post('/admin/test-access',json={'action':'resume','revision':'b'*32},headers=h).status_code==403
