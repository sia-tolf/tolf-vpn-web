"""Apply the routing contract to the exact deployed 2.6 API, including passwords."""
import importlib.util
import sqlite3
import uuid
from pathlib import Path
import pytest
import test_routing as shared
from test_routing import (test_modes_survive_creation_retry_and_reissue,
                         test_reject_before_provisioning,
                         test_route_failure_has_no_installation_link_and_retries_same_device)

ROOT = Path(__file__).resolve().parents[2]

@pytest.fixture
def api(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('windows26', ROOT/'setup/windows/compat-2.6/tolf_windows.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    monkeypatch.setattr(module, '__file__', str(ROOT/'setup/windows/tolf_windows.py'))
    monkeypatch.setattr(shared, 'w', module)
    yield from shared.api.__wrapped__(tmp_path)


def test_password_show_rotate_and_retry_keep_selected_route(api):
    client,ctx,calls,assigned=api
    passwords={};rotations=[];original=ctx['provision_on_riga']
    def provision(action,device,server='riga',mode=None):
        value=original('profile' if action=='rotate' else action,device,server,mode)
        if action=='rotate':
            rotations.append(device);passwords[device]='TEST_ONLY_CHANGED'
        if action in ('profile','rotate') and device in passwords: value['password']=passwords[device]
        return value
    ctx['provision_on_riga']=provision
    result=client.post('/windows/devices',json={'requestId':str(uuid.uuid4()),'name':'PC','server':'moscow','localId':'lv'}).json()
    device=result['device']['id'];prefix='/windows/devices/'+device
    shown=client.post(prefix+'/password');assert shown.status_code==200
    assert 'no-store' in shown.headers['cache-control']
    change={'requestId':str(uuid.uuid4())}
    changed=client.post(prefix+'/password/rotate',json=change)
    assert changed.status_code==200,changed.text
    assert changed.json()['password']=='TEST_ONLY_CHANGED'
    assert client.post(prefix+'/password/rotate',json=change).json()==changed.json()
    assert rotations==[device]
    assert client.get(result['profileUrl'].replace('https://api.tolf.is','')).status_code==404
    assert assigned[device]==('moscow','lv')
    assert all((node,mode)==('moscow','lv') for action,_,node,mode in calls if action=='profile')
    assert client.get('/windows/capabilities').json()['passwordManagement'] is True


def test_existing_moscow_device_and_old_controller(api):
    client,ctx,calls,assigned=api
    from fastapi import HTTPException
    def unavailable(*args): raise HTTPException(503,'old controller')
    ctx['windows_routing_rpc']=unavailable
    caps=client.get('/windows/capabilities').json()
    assert caps['installerVersion']=='2.6.0'
    assert caps['routingModes']=={'riga':['sr'],'moscow':['']}
    result=client.post('/windows/devices',json={'requestId':str(uuid.uuid4()),'name':'Existing Moscow','server':'moscow'})
    assert result.status_code==200,result.text
    device=result.json()['device']['id']
    with sqlite3.connect(ctx['DB']) as c:
        c.execute('DELETE FROM windows_device_routes WHERE device_id=?',(device,))
    row=client.get('/windows/devices').json()['devices'][0]
    assert row['server']=='moscow' and row['localId']==''
    assert client.post('/windows/devices/'+device+'/profile',json={}).status_code==200
    assert not assigned


def test_deployed_source_matches_hash():
    import hashlib
    source=(ROOT/'tests/windows/fixtures/windows-2.6.0.py').read_bytes()
    assert len(source)==23070
    assert hashlib.sha256(source).hexdigest()=='3a433a1842a9fee59dfee99700824659b4e332d3cabdd2cb6119a092e29fbe12'


def test_api_only_updater_payloads():
    import ast,base64,hashlib,zlib
    tree=ast.parse((ROOT/'setup/windows/update-routing-2.6.py').read_text())
    values={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
    assert set(values['PAYLOADS'])=={'tolf_windows.py','tolf_windows_routes.py'}
    for name,payload in values['PAYLOADS'].items():
        data=zlib.decompress(base64.b64decode(payload))
        assert hashlib.sha256(data).hexdigest()==values['HASHES'][name]
        source=ROOT/'setup/windows'/('compat-2.6/'+name if name=='tolf_windows.py' else name)
        assert data==source.read_bytes()
    assert '3a433a1842a9fee59dfee99700824659b4e332d3cabdd2cb6119a092e29fbe12' in values['EXPECTED']
