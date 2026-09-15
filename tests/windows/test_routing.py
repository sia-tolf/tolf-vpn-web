import contextlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import types
import uuid

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'setup/windows'))
import tolf_windows as w
import tolf_windows_routes as routes


@pytest.fixture
def api(tmp_path):
    account = str(uuid.uuid4())
    profiles = tmp_path/'profiles'; profiles.mkdir()
    calls = []; assigned = {}; credentials = {}
    def provision(action, device, server='riga', mode=None):
        calls.append((action, device, server, mode))
        if action == 'create': credentials.setdefault(device, {'username': 'user_'+uuid.UUID(device).hex, 'password': 'TEST_ONLY_NOT_A_REAL_SECRET'})
        if action in ('create','profile'): return {**credentials[device], 'server': server, 'localId': mode}
        return {'status': 'ok'}
    def rpc(action, *args):
        if action == 'capabilities': return {'status':'ok', 'protocol':1, 'modes':{k:list(v) for k,v in routes.MODES.items()}}
        if action == 'apply':
            device, server, mode = args; mode = '' if mode == 'default' else mode
            assigned[device] = (server, mode)
            return {'status': 'ok', 'server': server, 'localId': mode}
        assigned.pop(args[0], None); return {'status':'ok'}
    ctx = {'DB': str(tmp_path/'db'), 'authenticated_user_id': lambda request: account,
           'provision_on_riga': provision, 'windows_routing_rpc': rpc,
           'remove_provisioned_vpn': lambda device, user: credentials.pop(device, None),
           'tolf_promos': types.SimpleNamespace(account_operation=lambda *args: contextlib.nullcontext()),
           'tolf_profiles': types.SimpleNamespace(PROFILE_DIR=profiles, initialize=lambda: None,
              _valid_secret=lambda value: isinstance(value,str) and bool(value), _atomic_write=lambda path, value: path.write_bytes(value))}
    app = FastAPI(); w.install(app, ctx)
    with TestClient(app) as client:
        yield client,ctx,calls,assigned


@pytest.mark.parametrize('server,mode', [(node,mode) for node,modes in routes.MODES.items() for mode in modes])
def test_modes_survive_creation_retry_and_reissue(api, server, mode):
    client,ctx,calls,assigned = api
    payload = {'requestId':str(uuid.uuid4()), 'name':'Test PC', 'server':server, 'localId':mode}
    result = client.post('/windows/devices', json=payload)
    assert result.status_code == 200, result.text
    data = result.json(); device = data['device']['id']
    assert (data['device']['server'], data['device']['localId']) == (server, mode)
    assert assigned[device] == (server, mode)
    assert client.post('/windows/devices', json=payload).json()['device']['id'] == device
    reissue = client.post('/windows/devices/'+device+'/profile', json={}).json()['profileUrl']
    config = client.post(reissue.replace('https://api.tolf.is','')+'/settings').json()
    assert config['server'] == routes.HOSTS[server]
    before = list(calls)
    wrong = dict(payload, localId='ru' if mode != 'ru' else 'sr')
    assert client.post('/windows/devices', json=wrong).status_code == 409
    assert calls == before
    assert client.post('/windows/devices/'+device+'/delete').status_code == 200
    assert device not in assigned


@pytest.mark.parametrize('selection', [{'server':'other'}, {'server':'riga','localId':'ch'}, {'server':'moscow','localId':'yt'}, {'server':[]}, {'localId':None}])
def test_reject_before_provisioning(api, selection):
    client,ctx,calls,assigned = api
    assert client.post('/windows/devices', json={'requestId':str(uuid.uuid4()), 'name':'Test', **selection}).status_code == 400
    assert not calls and not assigned


def test_old_controller_does_not_advertise_or_silently_substitute_modes(api):
    client,ctx,calls,assigned = api
    def unavailable(*args): raise HTTPException(503, 'old server')
    ctx['windows_routing_rpc'] = unavailable
    assert client.get('/windows/capabilities').json()['routingModes'] == {'riga':['sr']}
    assert client.post('/windows/devices', json={'requestId':str(uuid.uuid4()), 'name':'Test', 'server':'moscow'}).status_code == 503
    assert not calls


def test_route_failure_has_no_installation_link_and_retries_same_device(api):
    client,ctx,calls,assigned = api
    original = ctx['windows_routing_rpc']
    def failed(action, *args):
        if action == 'apply': raise HTTPException(503, 'node unreachable')
        return original(action,*args)
    ctx['windows_routing_rpc'] = failed
    payload = {'requestId':str(uuid.uuid4()), 'name':'Test', 'server':'moscow','localId':'lv'}
    assert client.post('/windows/devices', json=payload).status_code == 503
    devices = client.get('/windows/devices').json()['devices']
    assert len(devices) == 1 and devices[0]['state'] == 'provisioning'
    assert not list(ctx['tolf_profiles'].PROFILE_DIR.iterdir())
    ctx['windows_routing_rpc'] = original
    result = client.post('/windows/devices', json=payload).json()
    assert result['device']['id'] == devices[0]['id'] and result['device']['state'] == 'active'


def test_legacy_schema_is_unchanged_for_rollback(tmp_path):
    w.CTX = {'DB':str(tmp_path/'db')}; w.initialize()
    with sqlite3.connect(w.CTX['DB']) as con:
        assert len(con.execute('PRAGMA table_info(windows_devices)').fetchall()) == 6
        # Exactly the INSERT used by the shipped 2.2 backend still works.
        con.execute('INSERT INTO windows_devices VALUES (?,?,?,?,?,?)', ('old','owner','Old PC','old_user','active','2026-01-01'))
    with w.db() as con:
        row = con.execute(w.DEVICE_QUERY).fetchone()
        assert (row['server'],row['local_id'],row['routing_managed']) == ('riga','sr',0)


def controller():
    spec = importlib.util.spec_from_file_location('controller', ROOT/'setup/windows/routing-control.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_controller_preserves_other_profiles_and_rolls_back_both_nodes(tmp_path, monkeypatch):
    c = controller(); monkeypatch.setattr(c,'ROOT',tmp_path)
    device = str(uuid.uuid4())
    old = {}; updated = {device:{'server':'moscow','mode':'lv'}}
    text = c.render('moscow',updated)
    assert 'eap_id = user_'+uuid.UUID(device).hex in text
    assert 'pools = vpn-pool-ee' in text
    assert text.index('tolf-win-dispatch') < text.index('tolf-win-'+uuid.UUID(device).hex)
    assert 'user0' not in text and 'connections' not in c.render('riga',updated)
    calls=[]
    monkeypatch.setattr(c,'preflight',lambda node:None)
    def replace(node, content):
        calls.append((node,content))
        if len(calls)==2: raise RuntimeError('Moscow reload failed')
    monkeypatch.setattr(c,'replace',replace)
    with pytest.raises(RuntimeError): c.change(old,updated)
    assert [node for node,_ in calls] == ['riga','moscow','riga','moscow']
    assert not (tmp_path/'assignments.json').exists()


def test_controller_never_loads_only_its_own_fragment(monkeypatch):
    c=controller(); scripts=[]
    monkeypatch.setattr(c,'run',lambda node,script:scripts.append(script))
    c.replace('riga',c.render('riga',{}))
    assert '--load-conns --file /etc/swanctl/swanctl.conf' in scripts[0]
    assert '--load-conns --file '+c.CONF not in scripts[0]
