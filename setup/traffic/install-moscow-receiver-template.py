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

RECEIVER = '__TOLF_RECEIVER_PAYLOAD__'
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
    for path in (service, receiver, secret, marker):
        checked_path(path)
    if directory.exists() or directory.is_symlink():
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
            raise SystemExit('ERROR: unsafe traffic directory')
        if not marker.exists() or marker.read_text() != 'TOLF_LOCAL_TRAFFIC_RECEIVER_V1\n':
            raise SystemExit('ERROR: unknown existing traffic installation')
        raise SystemExit('ERROR: traffic directory already exists; use a versioned update installer')
    if service.exists():
        if 'TOLF_LOCAL_TRAFFIC_RECEIVER_V1' not in service.read_text():
            raise SystemExit('ERROR: existing service needs manual integration')
        raise SystemExit('ERROR: receiver already installed; use a versioned update installer')
    if receiver.exists():
        raise SystemExit('ERROR: existing receiver needs manual integration')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.bind(('127.0.0.1', 18130))
    backup = Path(tempfile.mkdtemp(prefix='tolf-traffic-receiver-backup.', dir='/etc'))
    started = False
    try:
        directory.mkdir(mode=0o700)
        Path('/usr/libexec').mkdir(mode=0o755, exist_ok=True)
        write_atomic(secret, secrets.token_hex(32) + '\n', 0o600)
        write_atomic(marker, 'TOLF_LOCAL_TRAFFIC_RECEIVER_V1\n', 0o600)
        write_atomic(receiver, RECEIVER, 0o700)
        write_atomic(service, SERVICE, 0o755)
        started = True
        subprocess.run([str(service), 'enable'], check=True)
        subprocess.run([str(service), 'start'], check=True)
        # Signed real UDP probe must get an Accounting-Response. It uses a
        # reserved synthetic identity and is removed before UK delivery exists.
        import struct
        timestamp = int(time.time())
        def attribute(kind, value):
            if isinstance(value, int):
                value = struct.pack('!I', value)
            return bytes((kind, len(value) + 2)) + value
        attributes = (attribute(1, b'__tolf_receiver_install_test__') +
                      attribute(44, secrets.token_hex(16).encode()) +
                      attribute(40, 1) + attribute(55, timestamp))
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
        print('OK: Moscow local accounting receiver installed and tested.')
        print('Listener: 127.0.0.1:18130/UDP')
        print('Spool: /etc/tolf-traffic/spool.db')
        print('VPN accounting: not enabled; VPN configuration unchanged.')
        print('Backup:', backup)
    except BaseException:
        if started:
            subprocess.run([str(service), 'stop'], check=False)
            subprocess.run([str(service), 'disable'], check=False)
        for path in (service, receiver):
            if path.exists():
                path.unlink()
        if directory.exists():
            shutil.move(str(directory), str(backup / 'failed-installation'))
        print('ERROR: receiver installation rolled back; VPN configuration unchanged.')
        raise


if __name__ == '__main__':
    main()
