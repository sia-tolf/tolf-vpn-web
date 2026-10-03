"""Local strongSwan accounting decoder and durable node spool.

Deployment is deliberately separate: this module never changes VPN settings.
Only use with a dedicated loopback receiver, not public RADIUS authentication.
"""
from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import socket
import sqlite3
import stat
import struct


def decode(packet, secret, received_at=None):
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise ValueError('Accounting secret must have at least 32 bytes')
    if len(packet) < 20 or len(packet) > 4096:
        raise ValueError('Invalid RADIUS packet length')
    code, identifier, length = struct.unpack('!BBH', packet[:4])
    if code != 4 or length != len(packet):
        raise ValueError('Expected an exact Accounting-Request')
    expected = hashlib.md5(packet[:4] + bytes(16) + packet[20:] + secret).digest()
    if not hmac.compare_digest(packet[4:20], expected):
        raise ValueError('Invalid request authenticator')
    attrs = {}
    offset = 20
    while offset < length:
        if offset + 2 > length:
            raise ValueError('Truncated attribute')
        kind, size = packet[offset:offset + 2]
        if size < 2 or offset + size > length:
            raise ValueError('Invalid attribute length')
        attrs.setdefault(kind, []).append(packet[offset + 2:offset + size])
        offset += size

    def one(kind, default=None):
        values = attrs.get(kind, [])
        if len(values) > 1:
            raise ValueError('Duplicate accounting field')
        if not values:
            if default is None:
                raise ValueError('Missing accounting field')
            return default
        return values[0]

    def number(kind, default=None):
        value = one(kind, default)
        if len(value) != 4:
            raise ValueError('Invalid integer attribute')
        return struct.unpack('!I', value)[0]

    def label(kind, limit):
        value = one(kind).decode('utf-8', errors='strict')
        if not value or len(value) > limit or any(ord(c) < 32 for c in value):
            raise ValueError('Invalid accounting identity')
        return value

    status = number(40)
    if status not in (1, 2, 3):
        raise ValueError('Unsupported accounting status')
    zero = bytes(4)
    # strongSwan 6.0.3 does not emit Event-Timestamp (FreeRADIUS examples may
    # show receiver-added attributes). Use receipt time minus Acct-Delay-Time,
    # and derive retry identity from session elapsed time instead of wall time.
    source_timestamp = 55 in attrs
    elapsed = number(46) if not source_timestamp and status != 1 else 0
    if source_timestamp:
        timestamp = number(55)
    else:
        now = datetime.now(timezone.utc).timestamp() if received_at is None else received_at
        timestamp = now - number(41, zero)
    upload = number(42, zero) + (number(52, zero) << 32)
    download = number(43, zero) + (number(53, zero) << 32)
    if status != 1 and (42 not in attrs or 43 not in attrs):
        raise ValueError('Missing traffic counters')
    if max(upload, download) > 2**63 - 1 or (status == 1 and (upload or download)):
        raise ValueError('Invalid cumulative counters')
    event = {
        'protocol': 'ikev2', 'sessionId': label(44, 256),
        'username': label(1, 256),
        'observedAt': datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec='microseconds'),
        'upload': upload, 'download': download,
        'kind': {1: 'start', 2: 'stop', 3: 'interim'}[status],
    }
    identity = dict(event)
    if not source_timestamp:
        identity.pop('observedAt')
        identity['sessionTime'] = elapsed
    canonical = json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()
    event['eventId'] = hashlib.sha256(canonical).hexdigest()
    # Preserve Proxy-State in order, per RFC 2866. The receiver otherwise
    # returns no attributes; request verification still covers all attributes.
    response_attrs = b''.join(bytes((33, len(v) + 2)) + v for v in attrs.get(33, []))
    header = struct.pack('!BBH', 5, identifier, 20 + len(response_attrs))
    digest = hashlib.md5(header + packet[4:20] + response_attrs + secret).digest()
    return event, header + digest + response_attrs


class Spool:
    """Keep source order and retry identities across receiver restarts."""
    def __init__(self, database):
        self.con = sqlite3.connect(str(database), timeout=10)
        self.con.execute('PRAGMA synchronous=FULL')
        with self.con:
            self.con.execute('CREATE TABLE IF NOT EXISTS events ('
                             'sequence INTEGER PRIMARY KEY AUTOINCREMENT,'
                             'event_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)')

    def record(self, event):
        payload = json.dumps(event, sort_keys=True, separators=(',', ':'))
        with self.con:
            row = self.con.execute('SELECT payload FROM events WHERE event_id=?',
                                   (event['eventId'],)).fetchone()
            if row:
                if row[0] != payload:
                    original = json.loads(row[0])
                    incoming = dict(event)
                    original.pop('observedAt')
                    incoming.pop('observedAt')
                    if original != incoming:
                        raise ValueError('Conflicting spool event')
                    # Missing source timestamps differ on retries. Preserve
                    # the first committed observation for stable UK delivery.
            else:
                self.con.execute('INSERT INTO events(event_id,payload) VALUES (?,?)',
                                 (event['eventId'], payload))

    def receive(self, packet, secret):
        event, response = decode(packet, secret)
        # Never acknowledge before the durable transaction has committed.
        self.record(event)
        return response

    def pending(self, limit=1000):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError('Invalid batch limit')
        return [json.loads(row[0]) for row in self.con.execute(
            'SELECT payload FROM events ORDER BY sequence LIMIT ?', (limit,))]

    def acknowledge(self, event_ids):
        if not isinstance(event_ids, list) or len(event_ids) > 1000:
            raise ValueError('Invalid acknowledgements')
        if any(not isinstance(x, str) or len(x) != 64 or
               any(c not in '0123456789abcdef' for c in x) for x in event_ids):
            raise ValueError('Invalid event ID')
        with self.con:
            self.con.executemany('DELETE FROM events WHERE event_id=?',
                                 [(x,) for x in event_ids])

    def close(self):
        self.con.close()


def serve(database, secret_file, port=18130):
    directory = Path(database).parent
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError('Spool directory must be private and owned by the service user')
    path = Path(database)
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise ValueError('Unsafe spool database')
    fd = os.open(secret_file, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise ValueError('Unsafe accounting secret file')
        secret = os.read(fd, 256).strip()
    finally:
        os.close(fd)
    if len(secret) < 32 or len(secret) > 128:
        raise ValueError('Invalid accounting secret length')
    os.umask(0o077)
    spool = Spool(path)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No public listener, no reuse-port and no authentication service.
        sock.bind(('127.0.0.1', port))
        logging.info('Local accounting receiver ready')
        while True:
            packet, peer = sock.recvfrom(4097)
            if peer[0] != '127.0.0.1':
                continue
            try:
                response = spool.receive(packet, secret)
                sock.sendto(response, peer)
            except (ValueError, UnicodeError, OverflowError):
                logging.warning('Rejected invalid accounting packet')
            except (sqlite3.Error, OSError):
                # No ACK on a storage failure. Never log packet contents or
                # the shared secret; supervise the receiver separately.
                logging.error('Accounting persistence or response failed')
    finally:
        sock.close()
        spool.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Loopback VPN accounting receiver')
    parser.add_argument('--database', required=True)
    parser.add_argument('--secret-file', required=True)
    parser.add_argument('--port', type=int, default=18130)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='tolf-traffic: %(levelname)s: %(message)s')
    serve(args.database, args.secret_file, args.port)
