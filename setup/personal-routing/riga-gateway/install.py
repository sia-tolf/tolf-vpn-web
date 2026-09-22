#!/usr/bin/python3
"""Install an exact-command relay; probe status without submitting a policy."""
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile

ROOT = Path('/opt/tolf-personal-routing-gateway')
BASE = Path('/usr/local/sbin')
MARKER = '# TOLF personal routing user0 gateway v1'
ROOT_BLOCK = '''
# TOLF personal routing user0 gateway v1
if [ "${1:-}" = personal-routing-user0 ]; then
    [ "$#" -eq 2 ] || exit 1
    case "$2" in status|apply) ;; *) exit 1 ;; esac
    exec /usr/bin/python3 /opt/tolf-personal-routing-gateway/gateway.py "$2"
fi
'''
SSH_BLOCK = '''
# TOLF personal routing user0 gateway v1
if [[ "${SSH_ORIGINAL_COMMAND:-}" =~ ^personal-routing-user0[[:space:]]+(status|apply)$ ]]; then
    exec sudo -n /usr/local/sbin/tolf-provision-root personal-routing-user0 "${BASH_REMATCH[1]}"
fi
'''


def patch(source, block):
    anchor = 'set -euo pipefail\n'
    if MARKER in source or source.count(anchor) != 1 or '/usr/local/sbin/tolf-' not in source:
        raise RuntimeError('Unexpected or already patched provisioning gate')
    return source.replace(anchor, anchor + block + '\n', 1)


def atomic(path, data, info):
    fd, name = tempfile.mkstemp(prefix='.routing-gate-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, info.st_mode & 0o777)
        os.chown(name, info.st_uid, info.st_gid)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    if os.geteuid() != 0 or socket.gethostname().split('.')[0] != 'EDISLV':
        raise RuntimeError('Run as root on Riga EDISLV')
    with open('/var/lock/tolf-provision.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if ROOT.exists() or ROOT.is_symlink():
            raise RuntimeError('Gateway directory already exists; inspect before retrying')
        stage = Path(__file__).resolve().parent
        payload = {name: (stage / name).read_bytes() for name in ('gateway.py', 'policy.py')}
        for name, data in payload.items():
            compile(data, name, 'exec')
        original, planned = {}, {}
        for name, block in [('tolf-provision-root', ROOT_BLOCK), ('tolf-provision-ssh', SSH_BLOCK)]:
            path = BASE / name
            if path.is_symlink():
                raise RuntimeError('Unexpected symlink')
            original[path] = (path.read_bytes(), path.stat())
            planned[path] = patch(original[path][0].decode(), block).encode()
            subprocess.run(['/bin/bash', '-n'], input=planned[path], check=True)
        # Read-only remote probe before changing either gate.
        subprocess.run(['/usr/bin/python3', str(stage / 'gateway.py'), 'status'], check=True, timeout=30)
        backup = Path(tempfile.mkdtemp(prefix='tolf-routing-gateway-backup-', dir='/root'))
        for path in original:
            shutil.copy2(path, backup / path.name)
        rollback = """#!/usr/bin/python3
import fcntl, hashlib, os, shutil, tempfile
from pathlib import Path
BACKUP = Path(__file__).resolve().parent
EXPECTED = EXPECTED_PLACEHOLDER
with open('/var/lock/tolf-provision.lock', 'a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    for name, digest in EXPECTED.items():
        path = Path('/usr/local/sbin') / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise SystemExit('Gate changed after installation; automatic rollback refused: ' + name)
    for name in EXPECTED:
        path = Path('/usr/local/sbin') / name
        fd, staged = tempfile.mkstemp(prefix='.routing-rollback-', dir=path.parent)
        os.close(fd)
        try:
            shutil.copy2(BACKUP / name, staged)
            info = (BACKUP / name).stat()
            os.chown(staged, info.st_uid, info.st_gid)
            os.replace(staged, path)
        finally:
            Path(staged).unlink(missing_ok=True)
    # Retain inert helper files for inspection; both command gates have been restored.
    print('OK: previous provisioning gates restored.')
""".replace('EXPECTED_PLACEHOLDER', repr({p.name: hashlib.sha256(d).hexdigest() for p, d in planned.items()}))
        compile(rollback, 'rollback.py', 'exec')
        (backup / 'rollback.py').write_text(rollback)
        print('Backup:', backup, flush=True)
        try:
            ROOT.mkdir(mode=0o700)
            for name, data in payload.items():
                target = ROOT / name
                target.write_bytes(data)
                target.chmod(0o600)
            for path, data in planned.items():
                if path.read_bytes() != original[path][0]:
                    raise RuntimeError('Provisioning gate changed during installation')
                atomic(path, data, original[path][1])
            subprocess.run([str(BASE / 'tolf-provision-root'), 'personal-routing-user0', 'status'],
                           check=True, timeout=30)
        except Exception:
            for path, (data, info) in original.items():
                atomic(path, data, info)
            if ROOT.exists():
                shutil.rmtree(ROOT)
            print('Previous provisioning gates restored.', flush=True)
            raise
        print('OK: Riga user0 routing gateway installed; status verified; no policy submitted.')
        print('Rollback: python3', backup / 'rollback.py')


if __name__ == '__main__':
    main()
