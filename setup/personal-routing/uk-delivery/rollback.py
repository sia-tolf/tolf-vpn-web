#!/usr/bin/python3
"""Restore only this API module and stop delivery, retaining current saved rules."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile

ROOT = Path('/opt/tolf-api')
UNIT = Path('/etc/systemd/system/tolf-personal-routing.service')
DB = '/var/lib/tolf-api/tolf.db'


def main():
    if os.geteuid() != 0:
        raise RuntimeError('Run as root')
    backup = Path(__file__).resolve().parent
    manifest = json.loads((backup / 'manifest.json').read_text())
    with open('/var/lock/tolf-personal-routing-install.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for name, digest in {**manifest['files'], str(UNIT): manifest['unitHash']}.items():
            if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
                raise RuntimeError('File changed after installation; rollback refused: ' + name)
        subprocess.run(['systemctl', 'disable', '--now', UNIT.name], check=True, timeout=60)
        with sqlite3.connect(DB) as con:
            con.execute('UPDATE vpn_personal_routing_delivery SET enabled=0')
        target = ROOT / 'tolf_personal_routing.py'
        fd, temp = tempfile.mkstemp(prefix='.routing-rollback-', dir=ROOT)
        os.close(fd)
        try:
            old = backup / target.name
            shutil.copy2(old, temp)
            os.chown(temp, old.stat().st_uid, old.stat().st_gid)
            os.replace(temp, target)
        finally:
            Path(temp).unlink(missing_ok=True)
        UNIT.unlink()
        # Keep inert helper modules and historical delivery rows for inspection.
        subprocess.run(['systemctl', 'daemon-reload'], check=True, timeout=30)
        subprocess.run(['systemctl', 'restart', 'tolf-api'], check=True, timeout=60)
        print('OK: storage-only API restored; delivery disabled; saved and node rules retained.')


if __name__ == '__main__':
    main()
