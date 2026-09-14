#!/usr/bin/python3
"""VICI session control. Deliberately restricted to test account 26.

Protocol: strongswan/strongswan src/libcharon/plugins/vici/README.md.
Never uses swanctl's human-readable output for authorization.
"""
import contextlib
import json
import os
import re
import select
import socket
import struct
import subprocess
import sys
import time

TEST_USER = 'user_0888048cac6e44d28aed9857aa31e9ed'
SOCKET = '/var/run/charon.vici'
SSH = ['/usr/bin/ssh', '-T', '-i', '/root/.ssh/id_ed25519_ike_users_sync',
       '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
       '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10',
       'root@10.31.0.1', '/usr/bin/socat STDIO UNIX-CONNECT:/var/run/charon.vici']


class ControlError(Exception):
    pass


def decode(data):
    """Decode length-delimited VICI, rejecting duplicate or malformed fields."""
    pos = 0
    root = {}
    stack = [root]
    current_list = None

    def take(n):
        nonlocal pos
        if pos + n > len(data):
            raise ControlError('truncated_message')
        value = data[pos:pos+n]
        pos += n
        return value

    def name():
        return take(take(1)[0]).decode('ascii')

    def value():
        return take(struct.unpack('!H', take(2))[0])

    while pos < len(data):
        kind = take(1)[0]
        if current_list is not None:
            if kind == 5:
                current_list.append(value())
            elif kind == 6:
                current_list = None
            else:
                raise ControlError('invalid_list')
            continue
        if kind == 2:
            if len(stack) == 1:
                raise ControlError('unexpected_section_end')
            stack.pop()
        elif kind in (1, 3, 4):
            key = name()
            if key in stack[-1]:
                raise ControlError('duplicate_field')
            if kind == 3:
                stack[-1][key] = value()
            elif kind == 1:
                child = {}
                stack[-1][key] = child
                stack.append(child)
                if len(stack) > 16:
                    raise ControlError('excessive_depth')
            else:
                current_list = []
                stack[-1][key] = current_list
        else:
            raise ControlError('invalid_element')
    if len(stack) != 1 or current_list is not None:
        raise ControlError('unclosed_message')
    return root


def named(name):
    data = name.encode('ascii')
    return bytes([len(data)]) + data


def encode(fields):
    return b''.join(b'\x03' + named(k) + struct.pack('!H', len(v)) + v
                    for k, v in fields.items())


class Vici:
    def __init__(self, read_fd, write_fd):
        self.read_fd, self.write_fd = read_fd, write_fd
        self.deadline = time.monotonic() + 25
        self.total = 0

    def wait(self, writing=False):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ControlError('transport_timeout')
        ready = select.select([] if writing else [self.read_fd],
                              [self.write_fd] if writing else [], [], remaining)
        if not ready[1 if writing else 0]:
            raise ControlError('transport_timeout')

    def read(self, size):
        output = bytearray()
        while len(output) < size:
            self.wait()
            part = os.read(self.read_fd, size - len(output))
            if not part:
                raise ControlError('transport_closed')
            output.extend(part)
        return bytes(output)

    def send(self, packet):
        data = struct.pack('!I', len(packet)) + packet
        while data:
            self.wait(True)
            written = os.write(self.write_fd, data)
            if not written:
                raise ControlError('transport_closed')
            data = data[written:]

    def receive(self):
        size = struct.unpack('!I', self.read(4))[0]
        self.total += size
        if not 1 <= size <= 512 * 1024 or self.total > 8 * 1024 * 1024:
            raise ControlError('response_too_large')
        return self.read(size)

    def request(self, command, fields=None):
        self.send(b'\x00' + named(command) + encode(fields or {}))
        packet = self.receive()
        if packet[0] != 1:
            raise ControlError('unexpected_response')
        return decode(packet[1:])

    def inventory(self):
        self.send(b'\x03' + named('list-sa'))
        if self.receive() != b'\x05':
            raise ControlError('event_registration_failed')
        self.send(b'\x00' + named('list-sas'))
        rows = []
        while True:
            packet = self.receive()
            if packet[0] == 1:
                if decode(packet[1:]) != {}:
                    raise ControlError('invalid_inventory_response')
                break
            prefix = b'\x07' + named('list-sa')
            if not packet.startswith(prefix):
                raise ControlError('unexpected_inventory_event')
            event = decode(packet[len(prefix):])
            if len(event) != 1 or not isinstance(next(iter(event.values())), dict):
                raise ControlError('invalid_inventory_event')
            rows.append(next(iter(event.values())))
            if len(rows) > 10000:
                raise ControlError('too_many_sessions')
        self.send(b'\x04' + named('list-sa'))
        if self.receive() != b'\x05':
            raise ControlError('event_unregistration_failed')
        return rows


@contextlib.contextmanager
def connect(node):
    if node == 'riga':
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(10)
            sock.connect(SOCKET)
            sock.setblocking(True)
            yield Vici(sock.fileno(), sock.fileno())
    elif node == 'moscow':
        process = subprocess.Popen(SSH, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, bufsize=0)
        try:
            yield Vici(process.stdout.fileno(), process.stdin.fileno())
        finally:
            process.stdin.close()
            process.stdout.close()
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
    else:
        raise ControlError('invalid_node')


def selector(row):
    # EAP authentication identity is required; never fall back to an IKE ID.
    if row.get('state') != b'ESTABLISHED' or row.get('remote-eap-id') != TEST_USER.encode():
        return None
    try:
        result = {key: row[key].decode('ascii') for key in
                  ('uniqueid', 'initiator-spi', 'responder-spi')}
    except (KeyError, AttributeError, UnicodeError):
        raise ControlError('invalid_test_session')
    validate_selector(result)
    return result


def validate_selector(item):
    if not re.fullmatch(r'[1-9][0-9]{0,9}', item['uniqueid']) or int(item['uniqueid']) > 4294967295:
        raise ControlError('invalid_session_id')
    for field in ('initiator-spi', 'responder-spi'):
        if not re.fullmatch(r'[0-9a-f]{16}', item[field]):
            raise ControlError('invalid_session_spi')


def operate(client, expected=None):
    rows = client.inventory()
    tests = [item for row in rows if (item := selector(row)) is not None]
    if expected is None:
        return {'status': 'ok', 'accountNumber': 26, 'sessions': tests}
    validate_selector(expected)
    matches = [row for row in rows if row.get('uniqueid') == expected['uniqueid'].encode()]
    if len(matches) != 1 or selector(matches[0]) != expected:
        raise ControlError('stale_or_forbidden_session')
    # List and terminate on the SAME socket: daemon restart closes it; no reconnect/retry.
    # Unique IKE IDs do not get reused during this daemon lifetime (except uint32 wrap).
    reply = client.request('terminate', {'ike-id': expected['uniqueid'].encode(),
                                       'timeout': b'5000', 'force': b'no'})
    if reply.get('success') != b'yes' or reply.get('matches') != b'1' or reply.get('terminated') != b'1':
        return {'status': 'unknown', 'error': 'disconnect_not_confirmed', 'accountNumber': 26}
    remaining = client.inventory()
    if any(row.get('uniqueid') == expected['uniqueid'].encode() for row in remaining):
        return {'status': 'unknown', 'error': 'disconnect_not_confirmed', 'accountNumber': 26}
    return {'status': 'ok', 'accountNumber': 26, 'disconnected': expected['uniqueid'],
            'reconnected': any(selector(row) is not None for row in remaining)}


def main():
    if os.geteuid() != 0:
        raise ControlError('root_required')
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == 'list':
        expected = None
    elif len(args) == 5 and args[0] == 'disconnect':
        expected = dict(zip(('uniqueid', 'initiator-spi', 'responder-spi'), args[2:]))
        validate_selector(expected)
    else:
        raise ControlError('invalid_arguments')
    with connect(args[1]) as client:
        result = operate(client, expected)
    result['node'] = args[1]
    print(json.dumps(result, separators=(',', ':')))
    return 0 if result['status'] == 'ok' else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ControlError, OSError, UnicodeError) as error:
        # Transport errors don't establish whether a sent terminate completed. Do not retry.
        print(json.dumps({'status': 'error', 'error': str(error) if isinstance(error, ControlError)
                          else 'transport_error'}))
        sys.exit(1)
