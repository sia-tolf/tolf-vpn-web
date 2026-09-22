#!/usr/bin/env python3
"""Upgrade known storage-only deployment; preserve the live Moscow pilot policy."""
import ast
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path('/opt/tolf-api')
DB = Path('/var/lib/tolf-api/tolf.db')
UNIT = Path('/etc/systemd/system/tolf-personal-routing.service')
OLD_HASH = '8b750e1af746ce863e99000ea5d48f5bdf7aec08fc7427489375a9d0acd932d9'
ACCOUNT = '6e4f2559-fa36-410c-8b09-b299055d1ed6'
OLD_RULES = {'riga': ['delfi.lv'], 'moscow': [], 'usa': []}
NEW_RULES = {'riga': [], 'moscow': ['delfi.lv'], 'usa': []}


def atomic(path, data, mode=0o644, uid=0, gid=0):
    fd, temp = tempfile.mkstemp(prefix='.routing-delivery-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, mode)
        os.chown(temp, uid, gid)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def command(args, **kwargs):
    return subprocess.run(args, check=True, timeout=60, **kwargs)


def health():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(15):
        try:
            with opener.open('http://127.0.0.1:8000/health', timeout=2) as reply:
                if reply.status != 200:
                    raise RuntimeError('API health failed')
            try:
                opener.open('http://127.0.0.1:8000/vpn/routing-rules', timeout=2)
            except urllib.error.HTTPError as error:
                if error.code == 401:
                    return
        except (OSError, RuntimeError):
            pass
        time.sleep(1)
    raise RuntimeError('API health/authentication check failed')


def check_source(con):
    con.row_factory = sqlite3.Row
    row = con.execute('SELECT * FROM vpn_personal_routing WHERE user_id=?', (ACCOUNT,)).fetchone()
    owners = con.execute('SELECT user_id FROM vpn_access WHERE vpn_username=?', ('user0',)).fetchall()
    if (row is None or row['revision'] != 1 or row['vpn_username'] != 'user0'
            or json.loads(row['rules_json']) != OLD_RULES
            or len(owners) != 1 or owners[0]['user_id'] != ACCOUNT):
        raise RuntimeError('Saved policy or account changed; refusing automatic migration')


def check_context():
    expected = {'RIGA_HOST': '188.214.39.114', 'RIGA_USER': 'tolfprov',
                'RIGA_KEY': '/opt/tolf-api/provision_ed25519',
                'RIGA_KNOWN_HOSTS': '/opt/tolf-api/.ssh/known_hosts'}
    found = {}
    for node in ast.parse((ROOT / 'main.py').read_text()).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in expected:
                    found[target.id] = ast.literal_eval(node.value)
    if found != expected or 'tolf_personal_routing.install(app, globals())' not in (ROOT / 'main.py').read_text():
        raise RuntimeError('API integration or SSH settings differ; inspect before installing')


def main():
    if os.geteuid() != 0 or socket.gethostname().split('.')[0] != 'EDISUK':
        raise RuntimeError('Run as root on EDISUK')
    with open('/var/lock/tolf-personal-routing-install.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        check_context()
        target = ROOT / 'tolf_personal_routing.py'
        before, info = target.read_bytes(), target.stat()
        if target.is_symlink() or hashlib.sha256(before).hexdigest() != OLD_HASH:
            raise RuntimeError('Storage module differs from the known version')
        stage = Path(__file__).resolve().parent
        names = ('tolf_personal_routing.py', 'tolf_routing_delivery.py', 'tolf_routing_contract.py')
        payload = {name: (stage / name).read_bytes() for name in names}
        for name, data in payload.items():
            compile(data, name, 'exec')
            if name != target.name and ((ROOT / name).exists() or (ROOT / name).is_symlink()):
                raise RuntimeError('Delivery module already exists')
        if UNIT.exists() or UNIT.is_symlink():
            raise RuntimeError('Delivery unit already exists')
        command(['systemctl', 'is-active', '--quiet', 'tolf-api'])
        health()
        sys.path.insert(0, str(stage))
        import tolf_routing_delivery as delivery
        import tolf_routing_contract as contract
        report = delivery.transport('status')
        delivery.validate_report(report, contract.bootstrap())
        if report['state'] not in ('applied', 'ready'):
            raise RuntimeError('Moscow bootstrap policy is not ready')
        username = command(['systemctl', 'show', 'tolf-api', '-p', 'User', '--value'],
                           capture_output=True, text=True).stdout.strip() or 'root'
        import pwd
        pwd.getpwnam(username)  # Reject unresolved/dynamic service users.
        # Verify the actual API service user can use the existing credential files.
        command(['/usr/sbin/runuser', '-u', username, '--'] + delivery.SSH +
                ['personal-routing-user0 status'], capture_output=True)
        unit = f'''[Unit]
Description=TOLF personal routing delivery for enrolled user0
After=network-online.target tolf-api.service
Wants=network-online.target

[Service]
Type=simple
User={username}
WorkingDirectory=/opt/tolf-api
ExecStart=/opt/tolf-api/venv/bin/python -u /opt/tolf-api/tolf_routing_delivery.py
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=true
TimeoutStopSec=45

[Install]
WantedBy=multi-user.target
'''.encode()
        backup = Path(tempfile.mkdtemp(prefix='routing-delivery-backup-', dir=ROOT))
        shutil.copy2(target, backup / target.name)
        with sqlite3.connect(DB.as_uri() + '?mode=ro', uri=True) as con:
            check_source(con)
            if con.execute("SELECT 1 FROM sqlite_master WHERE name='vpn_personal_routing_delivery'").fetchone():
                raise RuntimeError('Delivery schema already exists')
            with sqlite3.connect(backup / 'tolf.db') as dest:
                con.backup(dest)
        manifest = {'files': {str(ROOT / n): hashlib.sha256(d).hexdigest() for n, d in payload.items()},
                    'unitHash': hashlib.sha256(unit).hexdigest()}
        (backup / 'manifest.json').write_text(json.dumps(manifest))
        shutil.copy2(stage / 'rollback.py', backup / 'rollback.py')
        print('Backup:', backup, flush=True)
        try:
            command(['systemctl', 'stop', 'tolf-api'])
            if target.read_bytes() != before:
                raise RuntimeError('API module changed during preparation')
            delivery.initialize(str(DB))
            with sqlite3.connect(DB) as con:
                con.execute('BEGIN IMMEDIATE')
                check_source(con)
                con.execute('''UPDATE vpn_personal_routing SET revision=2,rules_json=?,
                    updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE user_id=? AND revision=1''',
                    (json.dumps(NEW_RULES, sort_keys=True, separators=(',', ':')), ACCOUNT))
                con.execute('INSERT INTO vpn_personal_routing_delivery(account_id,enabled) VALUES (?,1)', (ACCOUNT,))
            for name, data in payload.items():
                atomic(ROOT / name, data, info.st_mode & 0o777, info.st_uid, info.st_gid)
            atomic(UNIT, unit)
            command(['systemctl', 'daemon-reload'])
            command(['systemctl', 'start', 'tolf-api'])
            health()
            command(['systemctl', 'enable', '--now', UNIT.name])
            # Observe at most 45 seconds. Delivery is asynchronous and retries independently.
            snapshot = None
            for _ in range(23):
                with delivery.connect(str(DB)) as con:
                    snapshot = delivery.enrich(con, ACCOUNT, 'user0',
                        {'revision': 2, 'routingRules': NEW_RULES, 'enforcementAvailable': False})
                if snapshot.get('appliedRevision') == 2 and snapshot.get('state') in ('applied', 'ready'):
                    break
                time.sleep(2)
            if snapshot.get('appliedRevision') != 2:
                raise RuntimeError('Delivery confirmation did not arrive; rolling code back')
        except Exception:
            # Source preference remains Moscow; never restore a whole live account database.
            subprocess.run(['systemctl', 'disable', '--now', UNIT.name], capture_output=True, timeout=60)
            with sqlite3.connect(DB) as con:
                if con.execute("SELECT 1 FROM sqlite_master WHERE name='vpn_personal_routing_delivery'").fetchone():
                    con.execute('UPDATE vpn_personal_routing_delivery SET enabled=0 WHERE account_id=?', (ACCOUNT,))
            atomic(target, before, info.st_mode & 0o777, info.st_uid, info.st_gid)
            for name in names[1:]:
                path = ROOT / name
                if path.exists() and path.read_bytes() == payload[name]:
                    path.unlink()
            if UNIT.exists() and UNIT.read_bytes() == unit:
                UNIT.unlink()
            command(['systemctl', 'daemon-reload'])
            command(['systemctl', 'start', 'tolf-api'])
            # Restart also covers failure after the new API was already started.
            command(['systemctl', 'restart', 'tolf-api'])
            health()
            print('Code rolled back; delivery disabled; saved Moscow preference retained.', flush=True)
            raise
        print('OK: UK automatic delivery enabled for user0; revision 2 confirmed by Moscow.')
        print(json.dumps(snapshot))
        print('Rollback: python3', backup / 'rollback.py')


if __name__ == '__main__':
    main()
