#!/usr/bin/python3
"""Install reversible Test #26 access control and provisioning guards."""
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
READER = BASE / 'tolf-admin-test-access'
MARKER = '# TOLF test account access control v1'
ROOT_BLOCK = """
# TOLF test account access control v1
if [ "${1:-}" = admin-test-access ]; then
    case "${2:-}" in
        status) [ "$#" -eq 2 ] || exit 1; exec /usr/local/sbin/tolf-admin-test-access status ;;
        suspend|resume) [ "$#" -eq 3 ] || exit 1; exec /usr/local/sbin/tolf-admin-test-access "$2" "$3" ;;
        *) exit 1 ;;
    esac
fi
"""
SSH_BLOCK = """
# TOLF test account access control v1
if [ "${SSH_ORIGINAL_COMMAND:-}" = 'admin-test-access status' ]; then
    exec sudo -n /usr/local/sbin/tolf-provision-root admin-test-access status
fi
if [[ "${SSH_ORIGINAL_COMMAND:-}" =~ ^admin-test-access[[:space:]]+(suspend|resume)[[:space:]]+([0-9a-f]{32})$ ]]; then
    exec sudo -n /usr/local/sbin/tolf-provision-root admin-test-access "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
fi
"""
PROVISION_GUARD = """
# TOLF Test26 provisioning guard v1
/usr/local/sbin/tolf-admin-test-access guard "$NEW_USER" || exit 1
case "$ACTION" in
    create-username|delete-username) /usr/local/sbin/tolf-admin-test-access guard "$ACCOUNT_ID" || exit 1 ;;
esac
"""
SYNC_GUARD = """
# TOLF Test26 sync guard v1
case "${1:-}:${2:-}" in
    push:user_0888048cac6e44d28aed9857aa31e9ed|delete:user_0888048cac6e44d28aed9857aa31e9ed)
        exec 8>/var/lock/tolf-admin-test-sync.lock
        flock -x 8
        /usr/local/sbin/tolf-admin-test-access guard "$2" || exit 1
        ;;
esac
"""


def insert_guard(source, anchor, block):
    marker = next(line for line in block.splitlines() if line.startswith('# TOLF'))
    if marker in source:
        if block.strip() not in source:
            raise RuntimeError('Existing access guard differs')
        return source
    if source.count(anchor) != 1:
        raise RuntimeError('Unsupported provisioning or synchronization script')
    return source.replace(anchor, block + '\n' + anchor, 1)


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
            text = patch(path.read_text(), block)
            if name == 'tolf-provision-root':
                text = insert_guard(text, 'find_user() {', PROVISION_GUARD)
            planned[path] = text.encode()
            subprocess.run(['/bin/bash', '-n'], input=planned[path], check=True)
        sync = BASE/'ike-users-sync.sh'
        planned[sync] = insert_guard(sync.read_text(), "DIR='/etc/swanctl/conf.d'", SYNC_GUARD).encode()
        subprocess.run(['/bin/sh', '-n'], input=planned[sync], check=True)
        backup = Path('/root/tolf-admin-test-access-backup-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid()))
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
                run = subprocess.run([str(BASE/'tolf-admin-test-control'), 'list', node], capture_output=True,
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
        print('OK: reversible access control installed; restricted to Test #26.')
        print('Installation did not suspend access or change VPN credentials.')
        for report in reports:
            print(report['node'] + ' VICI: OK; Test sessions: ' + str(len(report['sessions'])))


if __name__ == '__main__':
    main()
