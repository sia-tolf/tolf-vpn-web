import importlib.util
from pathlib import Path
import runpy
import subprocess
import pytest

path=Path(__file__).resolve().parents[3]/'setup/admin/nodes/test_access.py'
spec=importlib.util.spec_from_file_location('test_access_impl',path)
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

@pytest.fixture
def env(tmp_path,monkeypatch):
    base=tmp_path/'vault';base.mkdir()
    conf=tmp_path/'test.conf';conf.write_bytes(b'ORIGINAL SECRET BYTES')
    allow=tmp_path/'allow';allow.touch()
    for name,value in {'BASE':base,'STATE':base/'state.json','VAULT':base/'credential.saved','CONF':conf,'ALLOW':allow}.items():monkeypatch.setattr(a,name,value)
    remote={'data':conf.read_bytes(),'terminated':0,'reloads':0}
    monkeypatch.setattr(a,'remote_digest',lambda:a.digest(remote['data']) if remote['data'] is not None else None)
    def command(text,data=None):
        if text.startswith('rm -f '):remote['data']=None
        elif data is not None:remote['data']=data
        else:raise AssertionError(text)
        return b''
    monkeypatch.setattr(a,'remote',command)
    monkeypatch.setattr(a,'reload_local',lambda:remote.update(reloads=remote['reloads']+1))
    monkeypatch.setattr(a,'terminate_test_sessions',lambda:remote.update(terminated=remote['terminated']+1))
    return remote


def test_roundtrip_keeps_exact_credentials(env):
    saved=a.CONF.read_bytes()
    result=a.change('suspend',a.ZERO)
    assert result['state']=='suspended'
    assert not a.CONF.exists() and env['data'] is None
    assert a.VAULT.read_bytes()==saved
    assert a.VAULT.stat().st_mode & 0o777 == 0o600
    with pytest.raises(a.AccessError):a.guard(a.USER)
    a.guard('customer')
    result=a.change('resume',result['revision'])
    assert result['state']=='active'
    assert a.CONF.read_bytes()==env['data']==saved
    assert not a.VAULT.exists()
    a.guard(a.USER)


def test_stale_request_does_nothing(env):
    result=a.change('suspend',a.ZERO)
    with pytest.raises(a.AccessError,match='stale_revision'):a.change('resume',a.ZERO)
    assert a.read_state()=={**a.read_state(),'state':'suspended'}
    assert env['data'] is None


def test_remote_failure_keeps_deny_gate_and_recoverable_secret(env,monkeypatch):
    saved=a.CONF.read_bytes()
    original=a.remote
    def failure(*args,**kwargs):raise a.AccessError('offline')
    monkeypatch.setattr(a,'remote',failure)
    with pytest.raises(a.AccessError):a.change('suspend',a.ZERO)
    assert a.read_state()['state']=='suspending'
    assert a.VAULT.read_bytes()==saved
    with pytest.raises(a.AccessError):a.guard(a.USER)
    monkeypatch.setattr(a,'remote',original)
    assert a.change('suspend',a.read_state()['revision'])['state']=='suspended'
    assert env['data'] is None


def test_resume_partial_is_not_reported_active(env,monkeypatch):
    state=a.change('suspend',a.ZERO)
    def failure():raise a.AccessError('reload_failed')
    monkeypatch.setattr(a,'reload_local',failure)
    with pytest.raises(a.AccessError):a.change('resume',state['revision'])
    assert a.read_state()['state']=='resuming'
    assert a.VAULT.exists()
    with pytest.raises(a.AccessError):a.guard(a.USER)
    monkeypatch.setattr(a,'reload_local',lambda:None)
    assert a.change('resume',a.read_state()['revision'])['state']=='active'


def test_mismatch_before_suspend_changes_nothing(env):
    env['data']=b'DIFFERENT SECRET'
    with pytest.raises(a.AccessError,match='node_credentials_differ'):a.change('suspend',a.ZERO)
    assert not a.STATE.exists() and a.CONF.exists()
    assert not a.VAULT.exists()


def test_missing_permission_prevents_restore(env):
    state=a.change('suspend',a.ZERO)
    a.ALLOW.unlink()
    with pytest.raises(a.AccessError):a.change('resume',state['revision'])
    assert env['data'] is None and not a.CONF.exists()


def test_corrupt_vault_not_restored(env):
    state=a.change('suspend',a.ZERO)
    a.VAULT.write_bytes(b'CORRUPT')
    with pytest.raises(a.AccessError):a.change('resume',state['revision'])
    assert env['data'] is None and not a.CONF.exists()


def test_session_failure_is_partial(env,monkeypatch):
    def failure():raise a.AccessError('test_disconnect_not_confirmed')
    monkeypatch.setattr(a,'terminate_test_sessions',failure)
    with pytest.raises(a.AccessError):a.change('suspend',a.ZERO)
    assert a.read_state()['state']=='suspending'
    assert not a.CONF.exists() and env['data'] is None


def test_install_guards_idempotent_and_shell_valid():
    m=runpy.run_path(str(path.with_name('install-access-template.py')))
    original="#!/bin/bash\nset -euo pipefail\n# /usr/local/sbin/tolf-provision\nfind_user() { :; }\n"
    patched=m['patch'](original,m['ROOT_BLOCK'])
    patched=m['insert_guard'](patched,'find_user() {',m['PROVISION_GUARD'])
    assert m['insert_guard'](patched,'find_user() {',m['PROVISION_GUARD'])==patched
    subprocess.run(['/bin/bash','-n'],input=patched,text=True,check=True)
    subprocess.run(['/bin/bash','-n'],input=m['SSH_BLOCK'],text=True,check=True)
    subprocess.run(['/bin/sh','-n'],input=m['SYNC_GUARD'],text=True,check=True)
    with pytest.raises(RuntimeError):m['insert_guard']('changed','find_user() {',m['PROVISION_GUARD'])
