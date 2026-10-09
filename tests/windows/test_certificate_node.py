"""Exercise the generated node operation with real OpenSSL and isolated files."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import types
import uuid

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'setup/windows'))
import tolf_windows_ca as ca


@pytest.fixture
def node(tmp_path, monkeypatch):
    routing_path = tmp_path / 'routing.py'
    routing_path.write_text("HOSTS={'moscow':('92.243.66.32','ikev2.tolf.is')}\n"
                            "POOLS={'moscow':{'':'vpn-pool'}}\n"
                            "def validate(*args): pass\n"
                            "def preflight(*args): pass\n")
    original = importlib.util.spec_from_file_location
    def spec(name, location, *args, **kwargs):
        if str(location) == '/usr/local/lib/tolf-windows-routing.py':
            location = routing_path
        return original(name, location, *args, **kwargs)
    monkeypatch.setattr(importlib.util, 'spec_from_file_location', spec)
    module_spec = original('tolf_certificate_node_test', ROOT / 'setup/windows/certificate-node.py')
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    swanroot = tmp_path / 'swanctl'
    for directory in ('conf.d', 'pubkey', 'x509', 'x509ca'):
        (swanroot / directory).mkdir(parents=True)
    bindir = tmp_path / 'bin'; bindir.mkdir()
    command_log = tmp_path / 'commands.log'
    (bindir / 'swanctl').write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$TOLF_TEST_COMMAND_LOG"\nexit 0\n')
    (bindir / 'swanctl').chmod(0o700)
    def run(node, body):
        body = body.replace('/etc/swanctl', str(swanroot))
        env = dict(os.environ, PATH=str(bindir)+os.pathsep+os.environ['PATH'],
                   TOLF_TEST_COMMAND_LOG=str(command_log))
        subprocess.run(['sh', '-n'], input=body, text=True, check=True)
        return subprocess.run(['sh', '-s'], input=body, text=True, env=env,
                              check=True, capture_output=True)
    module.routing.run = run
    monkeypatch.setattr(module.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(module, 'open', lambda *args: (tmp_path / 'lock').open('a'), raising=False)
    ca.initialize(tmp_path / 'ca')
    authority = ca.Authority(tmp_path / 'ca')
    device = str(uuid.uuid4())
    issued = authority.issue(device)
    certificate = issued['certificate']
    from cryptography import x509
    public = x509.load_pem_x509_certificate(certificate).public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    data = dict(certificate=certificate.decode(), ca=authority.cert.public_bytes(
        serialization.Encoding.PEM).decode(), publicKey=public.decode())
    def apply(payload=None, target=None):
        monkeypatch.setattr(sys, 'stdin', io.StringIO(json.dumps(payload or data)))
        return module.main(['apply', target or device, 'moscow', 'default'])
    return types.SimpleNamespace(apply=apply, root=swanroot, device=device,
                                 data=data, commands=command_log, authority=authority)


def test_ca_authentication_keeps_client_material_out_of_trust_directories(node):
    node.apply()
    compact = uuid.UUID(node.device).hex
    conf = (node.root / 'conf.d' / ('tolf-cert-'+compact+'.conf')).read_text()
    assert 'cacerts = tolf-windows-ca.pem' in conf
    assert 'id = "CN=tolf-win-'+compact+'.tolf.is"' in conf
    assert 'pubkeys =' not in conf and 'certs =' not in conf.replace('cacerts =', '')
    assert 'esp_proposals = aes256-sha256-modp2048-none' in conf
    assert not list((node.root / 'x509').iterdir())
    assert not list((node.root / 'pubkey').iterdir())
    assert (node.root / 'tolf-certificates' / ('tolf-cert-'+compact+'.pem')).is_file()
    node.apply()
    assert '--clear' not in node.commands.read_text()
    assert not list(node.root.glob('.tolf-cert-ca.*'))


def test_mismatched_public_key_is_rejected_before_configuration_changes(node):
    node.apply()
    conf = next((node.root / 'conf.d').glob('*.conf'))
    original = conf.read_bytes()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key().public_bytes(serialization.Encoding.PEM,
                                          serialization.PublicFormat.SubjectPublicKeyInfo)
    with pytest.raises(subprocess.CalledProcessError):
        node.apply(dict(node.data, publicKey=public.decode()))
    assert conf.read_bytes() == original


def test_certificate_cannot_be_assigned_to_another_device(node):
    with pytest.raises(subprocess.CalledProcessError):
        node.apply(target=str(uuid.uuid4()))
    assert not list((node.root / 'conf.d').iterdir())


def test_pinned_ca_cannot_be_replaced(node, tmp_path):
    node.apply()
    ca.initialize(tmp_path / 'other-ca')
    other = ca.Authority(tmp_path / 'other-ca')
    with pytest.raises(subprocess.CalledProcessError):
        node.apply(dict(node.data, ca=other.cert.public_bytes(serialization.Encoding.PEM).decode()))
    assert (node.root / 'x509ca/tolf-windows-ca.pem').read_text() == node.data['ca']


def test_legacy_trusted_material_requires_explicit_migration(node):
    compact = uuid.UUID(node.device).hex
    legacy = node.root / 'pubkey' / ('tolf-cert-'+compact+'.pem')
    legacy.write_text(node.data['publicKey'])
    with pytest.raises(subprocess.CalledProcessError):
        node.apply()
    assert not list((node.root / 'conf.d').iterdir())
    assert legacy.is_file()
