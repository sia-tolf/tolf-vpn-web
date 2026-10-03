#!/usr/bin/python3
"""Stage only the local receiver; VPN accounting activation is separate."""
import hashlib
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import stat
import subprocess
import tempfile
import time

RECEIVER = '"""Local strongSwan accounting decoder and durable node spool.\n\nDeployment is deliberately separate: this module never changes VPN settings.\nOnly use with a dedicated loopback receiver, not public RADIUS authentication.\n"""\nfrom datetime import datetime, timezone\nimport hashlib\nimport hmac\nimport json\nimport logging\nimport os\nfrom pathlib import Path\nimport socket\nimport sqlite3\nimport stat\nimport struct\n\n\ndef decode(packet, secret, received_at=None):\n    if not isinstance(secret, bytes) or len(secret) < 32:\n        raise ValueError(\'Accounting secret must have at least 32 bytes\')\n    if len(packet) < 20 or len(packet) > 4096:\n        raise ValueError(\'Invalid RADIUS packet length\')\n    code, identifier, length = struct.unpack(\'!BBH\', packet[:4])\n    if code != 4 or length != len(packet):\n        raise ValueError(\'Expected an exact Accounting-Request\')\n    expected = hashlib.md5(packet[:4] + bytes(16) + packet[20:] + secret).digest()\n    if not hmac.compare_digest(packet[4:20], expected):\n        raise ValueError(\'Invalid request authenticator\')\n    attrs = {}\n    offset = 20\n    while offset < length:\n        if offset + 2 > length:\n            raise ValueError(\'Truncated attribute\')\n        kind, size = packet[offset:offset + 2]\n        if size < 2 or offset + size > length:\n            raise ValueError(\'Invalid attribute length\')\n        attrs.setdefault(kind, []).append(packet[offset + 2:offset + size])\n        offset += size\n\n    def one(kind, default=None):\n        values = attrs.get(kind, [])\n        if len(values) > 1:\n            raise ValueError(\'Duplicate accounting field\')\n        if not values:\n            if default is None:\n                raise ValueError(\'Missing accounting field\')\n            return default\n        return values[0]\n\n    def number(kind, default=None):\n        value = one(kind, default)\n        if len(value) != 4:\n            raise ValueError(\'Invalid integer attribute\')\n        return struct.unpack(\'!I\', value)[0]\n\n    def label(kind, limit):\n        value = one(kind).decode(\'utf-8\', errors=\'strict\')\n        if not value or len(value) > limit or any(ord(c) < 32 for c in value):\n            raise ValueError(\'Invalid accounting identity\')\n        return value\n\n    status = number(40)\n    if status not in (1, 2, 3):\n        raise ValueError(\'Unsupported accounting status\')\n    zero = bytes(4)\n    # strongSwan 6.0.3 does not emit Event-Timestamp (FreeRADIUS examples may\n    # show receiver-added attributes). Use receipt time minus Acct-Delay-Time,\n    # and derive retry identity from session elapsed time instead of wall time.\n    source_timestamp = 55 in attrs\n    elapsed = number(46) if not source_timestamp and status != 1 else 0\n    if source_timestamp:\n        timestamp = number(55)\n    else:\n        now = datetime.now(timezone.utc).timestamp() if received_at is None else received_at\n        timestamp = now - number(41, zero)\n    upload = number(42, zero) + (number(52, zero) << 32)\n    download = number(43, zero) + (number(53, zero) << 32)\n    if status != 1 and (42 not in attrs or 43 not in attrs):\n        raise ValueError(\'Missing traffic counters\')\n    if max(upload, download) > 2**63 - 1 or (status == 1 and (upload or download)):\n        raise ValueError(\'Invalid cumulative counters\')\n    event = {\n        \'protocol\': \'ikev2\', \'sessionId\': label(44, 256),\n        \'username\': label(1, 256),\n        \'observedAt\': datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec=\'microseconds\'),\n        \'upload\': upload, \'download\': download,\n        \'kind\': {1: \'start\', 2: \'stop\', 3: \'interim\'}[status],\n    }\n    identity = dict(event)\n    if not source_timestamp:\n        identity.pop(\'observedAt\')\n        identity[\'sessionTime\'] = elapsed\n    canonical = json.dumps(identity, sort_keys=True, separators=(\',\', \':\')).encode()\n    event[\'eventId\'] = hashlib.sha256(canonical).hexdigest()\n    # Preserve Proxy-State in order, per RFC 2866. The receiver otherwise\n    # returns no attributes; request verification still covers all attributes.\n    response_attrs = b\'\'.join(bytes((33, len(v) + 2)) + v for v in attrs.get(33, []))\n    header = struct.pack(\'!BBH\', 5, identifier, 20 + len(response_attrs))\n    digest = hashlib.md5(header + packet[4:20] + response_attrs + secret).digest()\n    return event, header + digest + response_attrs\n\n\nclass Spool:\n    """Keep source order and retry identities across receiver restarts."""\n    def __init__(self, database):\n        self.con = sqlite3.connect(str(database), timeout=10)\n        self.con.execute(\'PRAGMA synchronous=FULL\')\n        with self.con:\n            self.con.execute(\'CREATE TABLE IF NOT EXISTS events (\'\n                             \'sequence INTEGER PRIMARY KEY AUTOINCREMENT,\'\n                             \'event_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)\')\n\n    def record(self, event):\n        payload = json.dumps(event, sort_keys=True, separators=(\',\', \':\'))\n        with self.con:\n            row = self.con.execute(\'SELECT payload FROM events WHERE event_id=?\',\n                                   (event[\'eventId\'],)).fetchone()\n            if row:\n                if row[0] != payload:\n                    original = json.loads(row[0])\n                    incoming = dict(event)\n                    original.pop(\'observedAt\')\n                    incoming.pop(\'observedAt\')\n                    if original != incoming:\n                        raise ValueError(\'Conflicting spool event\')\n                    # Missing source timestamps differ on retries. Preserve\n                    # the first committed observation for stable UK delivery.\n            else:\n                self.con.execute(\'INSERT INTO events(event_id,payload) VALUES (?,?)\',\n                                 (event[\'eventId\'], payload))\n\n    def receive(self, packet, secret):\n        event, response = decode(packet, secret)\n        # Never acknowledge before the durable transaction has committed.\n        self.record(event)\n        return response\n\n    def pending(self, limit=1000):\n        if type(limit) is not int or not 1 <= limit <= 1000:\n            raise ValueError(\'Invalid batch limit\')\n        return [json.loads(row[0]) for row in self.con.execute(\n            \'SELECT payload FROM events ORDER BY sequence LIMIT ?\', (limit,))]\n\n    def acknowledge(self, event_ids):\n        if not isinstance(event_ids, list) or len(event_ids) > 1000:\n            raise ValueError(\'Invalid acknowledgements\')\n        if any(not isinstance(x, str) or len(x) != 64 or\n               any(c not in \'0123456789abcdef\' for c in x) for x in event_ids):\n            raise ValueError(\'Invalid event ID\')\n        with self.con:\n            self.con.executemany(\'DELETE FROM events WHERE event_id=?\',\n                                 [(x,) for x in event_ids])\n\n    def close(self):\n        self.con.close()\n\n\ndef serve(database, secret_file, port=18130):\n    directory = Path(database).parent\n    info = directory.lstat()\n    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:\n        raise ValueError(\'Spool directory must be private and owned by the service user\')\n    path = Path(database)\n    if path.exists() or path.is_symlink():\n        info = path.lstat()\n        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:\n            raise ValueError(\'Unsafe spool database\')\n    fd = os.open(secret_file, os.O_RDONLY | os.O_NOFOLLOW)\n    try:\n        info = os.fstat(fd)\n        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:\n            raise ValueError(\'Unsafe accounting secret file\')\n        secret = os.read(fd, 256).strip()\n    finally:\n        os.close(fd)\n    if len(secret) < 32 or len(secret) > 128:\n        raise ValueError(\'Invalid accounting secret length\')\n    os.umask(0o077)\n    spool = Spool(path)\n    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)\n    try:\n        # No public listener, no reuse-port and no authentication service.\n        sock.bind((\'127.0.0.1\', port))\n        logging.info(\'Local accounting receiver ready\')\n        while True:\n            packet, peer = sock.recvfrom(4097)\n            if peer[0] != \'127.0.0.1\':\n                continue\n            try:\n                response = spool.receive(packet, secret)\n                sock.sendto(response, peer)\n            except (ValueError, UnicodeError, OverflowError):\n                logging.warning(\'Rejected invalid accounting packet\')\n            except (sqlite3.Error, OSError):\n                # No ACK on a storage failure. Never log packet contents or\n                # the shared secret; supervise the receiver separately.\n                logging.error(\'Accounting persistence or response failed\')\n    finally:\n        sock.close()\n        spool.close()\n\n\nif __name__ == \'__main__\':\n    import argparse\n    parser = argparse.ArgumentParser(description=\'Loopback VPN accounting receiver\')\n    parser.add_argument(\'--database\', required=True)\n    parser.add_argument(\'--secret-file\', required=True)\n    parser.add_argument(\'--port\', type=int, default=18130)\n    args = parser.parse_args()\n    logging.basicConfig(level=logging.INFO, format=\'tolf-traffic: %(levelname)s: %(message)s\')\n    serve(args.database, args.secret_file, args.port)\n'
SERVICE = '''#!/bin/sh /etc/rc.common
# TOLF_LOCAL_TRAFFIC_RECEIVER_V1
USE_PROCD=1
START=85
STOP=15

start_service() {
    procd_open_instance
    procd_set_param command /usr/bin/python3 /usr/libexec/tolf-radius-accounting.py --database /etc/tolf-traffic/spool.db --secret-file /etc/tolf-traffic/radius.secret
    procd_set_param respawn 3600 5 5
    procd_set_param stdout 1
    procd_set_param stderr 1
    procd_close_instance
}
'''


def checked_path(path):
    if path.is_symlink():
        raise SystemExit('ERROR: unexpected symlink: ' + str(path))
    if path.exists() and (not path.is_file() or path.stat().st_uid != 0):
        raise SystemExit('ERROR: unexpected file ownership/type: ' + str(path))


def write_atomic(path, content, mode):
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    # All wrong-server checks precede filesystem/service changes.
    if os.geteuid() != 0:
        raise SystemExit('ERROR: run as root on Moscow OpenWrt')
    if not shutil.which('ip'):
        raise SystemExit('ERROR: this installer requires Moscow OpenWrt')
    probe = subprocess.run(['ip', '-4', 'addr', 'show', 'dev', 'br-lan'],
                           text=True, capture_output=True, check=False)
    address = probe.stdout if probe.returncode == 0 else ''
    if not re.search(r'\binet 92\.243\.66\.32/', address) or not Path('/etc/ocserv-moscow/ocserv.conf').is_file():
        raise SystemExit('ERROR: this installer is only for Moscow OpenWrt')
    if not Path('/etc/rc.common').is_file() or not Path('/usr/bin/python3').is_file():
        raise SystemExit('ERROR: OpenWrt procd/Python required')
    import sqlite3
    compile(RECEIVER, 'radius_accounting.py', 'exec')
    namespace = {'__name__': 'installer_preflight'}
    exec(compile(RECEIVER, 'radius_accounting.py', 'exec'), namespace)
    check = namespace['Spool'](':memory:')
    check.close()
    directory = Path('/etc/tolf-traffic')
    service = Path('/etc/init.d/tolf-traffic-accounting')
    receiver = Path('/usr/libexec/tolf-radius-accounting.py')
    secret = directory / 'radius.secret'
    marker = directory / 'receiver-version'
    upgrading = False
    for path in (service, receiver, secret, marker):
        checked_path(path)
    if directory.exists() or directory.is_symlink():
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
            raise SystemExit('ERROR: unsafe traffic directory')
        if not marker.exists() or marker.read_text() != 'TOLF_LOCAL_TRAFFIC_RECEIVER_V1\n':
            raise SystemExit('ERROR: unknown existing traffic installation')
        old_hash = '7dd020aa889407284ee663da95f0dacd3cabbdbd3c363ae3292bf6372dd47734'
        if (not receiver.exists() or hashlib.sha256(receiver.read_bytes()).hexdigest() != old_hash or
                not service.exists() or service.read_text() != SERVICE):
            raise SystemExit('ERROR: unsupported receiver version; installation unchanged')
        upgrading = True
        # This compatibility update is only for the pre-activation stage.
        configs = [Path('/etc/strongswan.conf')]
        configs.extend(Path('/etc/strongswan.d').rglob('*.conf'))
        for config in configs:
            if config.is_file() and re.search(r'^\s*accounting\s*=\s*(yes|true|1)\b',
                    config.read_text(errors='replace'), re.MULTILINE):
                raise SystemExit('ERROR: accounting already enabled; requires a live update installer')
    if service.exists() and not upgrading:
        if 'TOLF_LOCAL_TRAFFIC_RECEIVER_V1' not in service.read_text():
            raise SystemExit('ERROR: existing service needs manual integration')
        raise SystemExit('ERROR: receiver already installed; use a versioned update installer')
    if receiver.exists() and not upgrading:
        raise SystemExit('ERROR: existing receiver needs manual integration')
    if not upgrading:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.bind(('127.0.0.1', 18130))
    backup = Path(tempfile.mkdtemp(prefix='tolf-traffic-receiver-backup.', dir='/etc'))
    started = False
    try:
        if upgrading:
            shutil.copy2(receiver, backup / receiver.name)
            subprocess.run([str(service), 'stop'], check=True)
        else:
            directory.mkdir(mode=0o700)
        Path('/usr/libexec').mkdir(mode=0o755, exist_ok=True)
        if not upgrading:
            write_atomic(secret, secrets.token_hex(32) + '\n', 0o600)
            write_atomic(marker, 'TOLF_LOCAL_TRAFFIC_RECEIVER_V1\n', 0o600)
        write_atomic(receiver, RECEIVER, 0o700)
        if not upgrading:
            write_atomic(service, SERVICE, 0o755)
        started = True
        if not upgrading:
            subprocess.run([str(service), 'enable'], check=True)
        subprocess.run([str(service), 'start'], check=True)
        # Signed real UDP probe must get an Accounting-Response. It uses a
        # reserved synthetic identity and is removed before UK delivery exists.
        import struct
        def attribute(kind, value):
            if isinstance(value, int):
                value = struct.pack('!I', value)
            return bytes((kind, len(value) + 2)) + value
        attributes = (attribute(1, b'__tolf_receiver_install_test__') +
                      attribute(44, secrets.token_hex(16).encode()) +
                      attribute(40, 1))
        header = struct.pack('!BBH', 4, 211, 20 + len(attributes))
        key = secret.read_bytes().strip()
        packet = header + hashlib.md5(header + bytes(16) + attributes + key).digest() + attributes
        event, expected = namespace['decode'](packet, key)
        success = False
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.settimeout(1)
            for attempt in range(10):
                probe.sendto(packet, ('127.0.0.1', 18130))
                try:
                    response, peer = probe.recvfrom(4096)
                except socket.timeout:
                    continue
                if peer == ('127.0.0.1', 18130) and secrets.compare_digest(response, expected):
                    success = True
                    break
        if not success:
            raise RuntimeError('Receiver did not acknowledge the signed test')
        # Stop first so queued retries cannot restore the synthetic record
        # after deletion. This first-stage installation has no VPN producer.
        subprocess.run([str(service), 'stop'], check=True)
        stopped = False
        for attempt in range(20):
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                try:
                    probe.bind(('127.0.0.1', 18130))
                    stopped = True
                    break
                except OSError:
                    time.sleep(0.25)
        if not stopped:
            raise RuntimeError('Receiver did not stop after the test')
        with sqlite3.connect(directory / 'spool.db') as con:
            row = con.execute('SELECT payload FROM events WHERE event_id=?', (event['eventId'],)).fetchone()
            if not row:
                raise RuntimeError('Receiver test was not durably stored')
            con.execute('DELETE FROM events WHERE event_id=?', (event['eventId'],))
        subprocess.run([str(service), 'start'], check=True)
        print('OK: Moscow local accounting receiver updated and tested.' if upgrading else
              'OK: Moscow local accounting receiver installed and tested.')
        print('Listener: 127.0.0.1:18130/UDP')
        print('Spool: /etc/tolf-traffic/spool.db')
        print('VPN accounting: not enabled; VPN configuration unchanged.')
        print('Backup:', backup)
    except BaseException:
        if started:
            subprocess.run([str(service), 'stop'], check=False)
            if not upgrading:
                subprocess.run([str(service), 'disable'], check=False)
        if upgrading:
            if (backup / receiver.name).exists():
                shutil.copy2(backup / receiver.name, receiver)
                subprocess.run([str(service), 'start'], check=False)
        else:
            for path in (service, receiver):
                if path.exists():
                    path.unlink()
            if directory.exists():
                shutil.move(str(directory), str(backup / 'failed-installation'))
        print('ERROR: receiver installation rolled back; VPN configuration unchanged.')
        raise


if __name__ == '__main__':
    main()
