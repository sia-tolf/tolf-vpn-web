#!/usr/bin/python3
"""Install read-only session inventory behind the existing provisioning gate."""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time

PAYLOAD = ''
HASH = ''
BASE = Path('/usr/local/sbin')
READER = BASE / 'tolf-admin-sessions'
MARKER = '# TOLF read-only admin sessions v1'
ROOT_BLOCK = '''
# TOLF read-only admin sessions v1
if [ "${1:-}" = admin-sessions ]; then
    [ "$#" -eq 2 ] || exit 1
    case "$2" in riga|moscow) ;; *) exit 1 ;; esac
    exec /usr/local/sbin/tolf-admin-sessions "$2"
fi
'''
SSH_BLOCK = '''
# TOLF read-only admin sessions v1
if [[ "${SSH_ORIGINAL_COMMAND:-}" =~ ^admin-sessions[[:space:]]+(riga|moscow)$ ]]; then
    exec sudo -n /usr/local/sbin/tolf-provision-root admin-sessions "${BASH_REMATCH[1]}"
fi
'''


def patch(source, block):
    if MARKER in source:
        if block.strip() not in source:
            raise RuntimeError('Existing admin integration differs')
        return source
    anchor = 'set -euo pipefail\n'
    if source.count(anchor) != 1 or '/usr/local/sbin/tolf-' not in source:
        raise RuntimeError('Unsupported provisioning script')
    return source.replace(anchor, anchor + block + '\n', 1)


def atomic(path, data, info=None):
    fd, name = tempfile.mkstemp(prefix='.'+path.name+'-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(name, (info.st_mode & 0o777) if info else 0o755)
        os.chown(name, info.st_uid if info else 0, info.st_gid if info else 0)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    if os.geteuid() != 0 or socket.gethostname() != 'EDISLV':
        raise SystemExit('Run as root on Riga EDISLV')
    with open('/var/lock/tolf-provision.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        reader = base64.b64decode(PAYLOAD)
        if hashlib.sha256(reader).hexdigest() != HASH:
            raise RuntimeError('Payload checksum mismatch')
        compile(reader, str(READER), 'exec')
        planned = {READER: reader}
        for name, block in [('tolf-provision-root', ROOT_BLOCK), ('tolf-provision-ssh', SSH_BLOCK)]:
            path = BASE/name
            planned[path] = patch(path.read_text(), block).encode()
            subprocess.run(['/bin/bash', '-n'], input=planned[path], check=True)
        backup = Path('/root/tolf-admin-sessions-backup-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid()))
        backup.mkdir(mode=0o700)
        original = {}
        for path in planned:
            original[path] = (path.read_bytes(), path.stat()) if path.exists() else None
            if path.exists():
                shutil.copy2(path, backup/path.name)
        print('Backup:', backup, flush=True)
        try:
            for path, data in planned.items():
                atomic(path, data, original[path][1] if original[path] else None)
            run = subprocess.run([str(READER), 'riga'], capture_output=True, text=True, timeout=30, check=True)
            report = json.loads(run.stdout)
            if report.get('status') != 'ok' or report.get('node') != 'riga':
                raise RuntimeError('Riga inventory validation failed')
        except Exception:
            for path, old in original.items():
                if old is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic(path, old[0], old[1])
            print('Previous files restored.', flush=True)
            raise
        print('OK: read-only session inventory installed. VPN configuration and sessions unchanged.')
        print('Riga sessions:', len(report['sessions']))
        run = subprocess.run([str(READER), 'moscow'], capture_output=True, text=True, timeout=30)
        try:
            report = json.loads(run.stdout)
            if run.returncode or report.get('status') != 'ok':
                raise ValueError('Moscow unavailable')
            print('Moscow sessions:', len(report['sessions']))
        except (ValueError, KeyError):
            print('Moscow inventory unavailable; do not interpret this as zero sessions.')


if __name__ == '__main__':
    main()
