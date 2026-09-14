import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]

def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT/'setup/admin/nodes'/filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

reader = module('reader', 'session_reader.py')
installer = module('installer', 'install-template.py')

def event(identity='remote-id=192.168.0.66 remote-eap-id=user_elena_udalova'):
    return 'list-sa event {ikev2-eap-domain {uniqueid=5436 state=ESTABLISHED '+identity+' remote-host=188.17.213.92 established=1782 remote-vips=[10.10.10.98] child-sas {one {uniqueid=4337 bytes-in=1501493 bytes-out=42890143} two {bytes-in=7 bytes-out=57}}}}\nlist-sas reply {}\n'

def test_valid_inventory():
    assert reader.parse_inventory('list-sas reply {}\n') == []
    value = reader.parse_inventory(event())[0]
    assert value['identity'] == 'user_elena_udalova'
    assert value['identitySource'] == 'remote-eap-id'
    assert value['id'] == 5436
    assert value['bytesIn'] == 1501500
    assert value['bytesOut'] == 42890200
    assert value['virtualAddresses'] == ['10.10.10.98']
    assert reader.parse_inventory(event('remote-id=user_irina_farafontova'))[0]['identitySource'] == 'remote-id'

@pytest.mark.parametrize('text', ['', 'connection failed', 'list-sas reply {}\nlist-sas reply {}', event().replace('list-sas reply {}',''), event().replace('uniqueid=5436','uniqueid=5436 uniqueid=1'), event().replace('bytes-in=7','bytes-in=invalid')])
def test_unknown_is_not_empty(text):
    with pytest.raises(ValueError):
        reader.parse_inventory(text)

def test_transport_failure_is_not_empty(monkeypatch):
    class Reply:
        returncode = 1
        stdout = 'list-sas reply {}'
    monkeypatch.setattr(reader.subprocess, 'run', lambda *a, **kw: Reply())
    with pytest.raises(RuntimeError):
        reader.read_node('moscow')
    with pytest.raises(ValueError):
        reader.read_node('moscow; touch /tmp/no')

def test_dispatch_patch():
    source = '#!/bin/bash\nset -euo pipefail\nexec /usr/local/sbin/tolf-provision-root "$@"\n'
    changed = installer.patch(source, installer.SSH_BLOCK)
    assert changed.endswith('exec /usr/local/sbin/tolf-provision-root "$@"\n')
    assert installer.patch(changed, installer.SSH_BLOCK) == changed
    with pytest.raises(RuntimeError):
        installer.patch('#!/bin/sh\n', installer.SSH_BLOCK)
