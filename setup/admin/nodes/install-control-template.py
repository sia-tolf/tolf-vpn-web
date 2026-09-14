#!/usr/bin/python3
"""Install structured session control restricted to Test account 26."""
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
READER = BASE / 'tolf-admin-test-control'
MARKER = '# TOLF test account session control v1'
ROOT_BLOCK = '''
# TOLF test account session control v1
if [ "${1:-}" = admin-test-sessions ]; then
    [ "$#" -eq 2 ] || exit 1
    exec /usr/local/sbin/tolf-admin-test-control list "$2"
fi
if [ "${1:-}" = admin-test-disconnect ]; then
    [ "$#" -eq 5 ] || exit 1
    exec /usr/local/sbin/tolf-admin-test-control disconnect "$2" "$3" "$4" "$5"
fi
'''
SSH_BLOCK = '''
# TOLF test account session control v1
if [[ "${SSH_ORIGINAL_COMMAND:-}" =~ ^admin-test-sessions[[:space:]]+(riga|moscow)$ ]]; then
    exec sudo -n /usr/local/sbin/tolf-provision-root admin-test-sessions "${BASH_REMATCH[1]}"
fi
if [[ "${SSH_ORIGINAL_COMMAND:-}" =~ ^admin-test-disconnect[[:space:]]+(riga|moscow)[[:space:]]+([1-9][0-9]{0,9})[[:space:]]+([0-9a-f]{16})[[:space:]]+([0-9a-f]{16})$ ]]; then
    exec sudo -n /usr/local/sbin/tolf-provision-root admin-test-disconnect "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}" "${BASH_REMATCH[4]}"
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
        backup = Path('/root/tolf-admin-test-control-backup-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid()))
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
            reports = []
            for node in ('riga', 'moscow'):
                run = subprocess.run([str(READER), 'list', node], capture_output=True,
                                     text=True, timeout=35)
                if run.returncode:
                    raise RuntimeError(node + ' VICI read probe failed: ' + run.stdout[-500:])
                report = json.loads(run.stdout)
                if report.get('status') != 'ok' or report.get('node') != node:
                    raise RuntimeError(node + ' VICI validation failed')
                reports.append(report)
        except Exception:
            for path, old in original.items():
                if old is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic(path, old[0], old[1])
            print('Previous files restored.', flush=True)
            raise
        print('OK: structured session control installed; restricted to Test account #26.')
        print('Installation only read session data. No VPN sessions disconnected.')
        for report in reports:
            print(report['node'] + ' VICI: OK; Test sessions: ' + str(len(report['sessions'])))


if __name__ == '__main__':
    main()
