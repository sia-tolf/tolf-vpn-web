import importlib.util
from pathlib import Path
import socket
import struct
import threading
import pytest

path = Path(__file__).resolve().parents[3] / 'setup/admin/nodes/test_control.py'
spec = importlib.util.spec_from_file_location('control', path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def row(user=m.TEST_USER, sid=b'5448'):
    return {'uniqueid': sid, 'state': b'ESTABLISHED', 'remote-id': b'',
            'remote-eap-id': user.encode(), 'initiator-spi': b'33c90b2d7d2b4919',
            'responder-spi': b'c13a2693c6783e0e'}


class Fake:
    def __init__(self, before, after=(), reply=None):
        self.before, self.after, self.calls = before, after, []
        self.reply = reply or {'success': b'yes', 'matches': b'1', 'terminated': b'1'}
    def inventory(self):
        return self.after if self.calls else self.before
    def request(self, command, fields):
        self.calls.append((command, fields))
        return self.reply


def test_exact_test_disconnect_only():
    client = Fake([row('user0', b'10'), row(), row('customer', b'11')], [row('customer', b'11')])
    result = m.operate(client, m.selector(row()))
    assert result['disconnected'] == '5448'
    assert client.calls == [('terminate', {'ike-id': b'5448', 'timeout': b'5000', 'force': b'no'})]


@pytest.mark.parametrize('change', [
    {'remote-eap-id': b'user0'}, {'remote-eap-id': b'customer'},
    {'remote-eap-id': b'', 'remote-id': m.TEST_USER.encode()},
    {'state': b'CONNECTING'}, {'uniqueid': b'5449'},
    {'initiator-spi': b'0000000000000000'}, {'responder-spi': b'0000000000000000'}])
def test_forbidden_or_replaced_no_command(change):
    client = Fake([{**row(), **change}])
    with pytest.raises(m.ControlError):
        m.operate(client, m.selector(row()))
    assert not client.calls


def test_missing_and_duplicate_no_command():
    for rows in ([], [row(), row()]):
        client = Fake(rows)
        with pytest.raises(m.ControlError):
            m.operate(client, m.selector(row()))
        assert not client.calls


def test_list_never_terminates():
    client = Fake([row('user0'), row()])
    assert len(m.operate(client)['sessions']) == 1
    assert not client.calls


def test_reconnection_reported():
    client = Fake([row()], [row(sid=b'5449')])
    assert m.operate(client, m.selector(row()))['reconnected'] is True


def test_unconfirmed_not_retried():
    client = Fake([row()], reply={'success': b'no'})
    assert m.operate(client, m.selector(row()))['status'] == 'unknown'
    assert len(client.calls) == 1


def test_native_empty_identity_and_embedded_delimiters():
    data = m.encode({'remote-id': b'', 'remote-eap-id': m.TEST_USER.encode(),
                     'untrusted': b'hello remote-eap-id=user0 {uniqueid=2}'})
    result = m.decode(data)
    assert result['remote-id'] == b''
    assert result['remote-eap-id'] == m.TEST_USER.encode()
    assert len(result) == 3


@pytest.mark.parametrize('data', [b'\x02', b'\x01\x01x', b'\x04\x01x', b'\x05\x00\x00',
                                  b'\x03\x01x\x00\x02a', m.encode({'x': b'a'}) * 2])
def test_bad_messages_rejected(data):
    with pytest.raises(m.ControlError):
        m.decode(data)


def test_binary_transport_fragmented_stream():
    a, b = socket.socketpair()
    failures = []
    def server():
        try:
            def receive():
                size = struct.unpack('!I', b.recv(4))[0]
                return b.recv(size)
            def send(payload):
                for octet in struct.pack('!I', len(payload)) + payload:
                    b.sendall(bytes([octet]))
            assert receive() == b'\x03' + m.named('list-sa')
            send(b'\x05')
            assert receive() == b'\x00' + m.named('list-sas')
            send(b'\x07' + m.named('list-sa') + b'\x01' + m.named('connection') + m.encode(row()) + b'\x02')
            send(b'\x01')
            assert receive() == b'\x04' + m.named('list-sa')
            send(b'\x05')
        except BaseException as exc:
            failures.append(exc)
        finally:
            b.close()
    worker = threading.Thread(target=server)
    worker.start()
    try:
        assert m.Vici(a.fileno(), a.fileno()).inventory() == [row()]
    finally:
        a.close()
        worker.join(timeout=3)
    assert not failures
    assert not worker.is_alive()


def test_installer_preserves_inventory_and_is_idempotent():
    import runpy
    import subprocess
    installer = runpy.run_path(str(path.with_name('install-control-template.py')))
    for key in ('ROOT_BLOCK', 'SSH_BLOCK'):
        original = '#!/bin/bash\nset -euo pipefail\n# existing /usr/local/sbin/tolf-provision\necho unchanged\n'
        patched = installer['patch'](original, installer[key])
        assert patched.endswith('echo unchanged\n')
        assert installer['patch'](patched, installer[key]) == patched
        subprocess.run(['/bin/bash', '-n'], input=patched, text=True, check=True)


def test_transport_rejects_oversized_frame():
    a, b = socket.socketpair()
    try:
        b.sendall(struct.pack('!I', 512 * 1024 + 1))
        with pytest.raises(m.ControlError, match='response_too_large'):
            m.Vici(a.fileno(), a.fileno()).receive()
    finally:
        a.close()
        b.close()


def test_ssh_is_fixed_binary_transport():
    assert '-n' not in m.SSH
    assert 'StrictHostKeyChecking=yes' in m.SSH
    assert m.SSH[-1] == '/usr/bin/socat STDIO UNIX-CONNECT:/var/run/charon.vici'
