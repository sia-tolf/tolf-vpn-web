"""New UI metadata is opt-in: installed 2.6 parsers still receive four fields."""
import importlib.util
import uuid
from pathlib import Path
import pytest
import test_routing as shared
ROOT=Path(__file__).resolve().parents[2]
@pytest.fixture
def api(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('windows261',ROOT/'setup/windows/compat-2.6.1/tolf_windows.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'__file__',str(ROOT/'setup/windows/tolf_windows.py'))
    monkeypatch.setattr(shared,'w',module)
    yield from shared.api.__wrapped__(tmp_path)

@pytest.mark.parametrize('server,mode',[('riga','ru'),('riga','sr'),('moscow',''),('moscow','lv')])
def test_labels_preserve_legacy_credentials_and_routing(api,server,mode):
    client,ctx,calls,assigned=api
    r=client.post('/windows/devices',json={'requestId':str(uuid.uuid4()),'name':'Рабочий компьютер','server':server,'localId':mode})
    assert r.status_code==200,r.text
    url=r.json()['profileUrl'].replace('https://api.tolf.is','')+'/settings'
    old=client.post(url);new=client.post(url+'?labels=true')
    assert old.status_code==new.status_code==200,new.text
    assert set(old.json())=={'deviceId','server','username','password'}
    data=new.json();assert data.pop('displayName')=='Рабочий компьютер'
    assert data.pop('routingMode')==mode
    assert data==old.json()
    assert 'no-store' in new.headers['cache-control']
    assert assigned[r.json()['device']['id']]==(server,mode)
    assert client.get('/windows/capabilities').json()['profileLabels'] is True
