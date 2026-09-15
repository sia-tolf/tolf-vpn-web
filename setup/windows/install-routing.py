#!/usr/bin/env python3
"""Install the routing controller on Riga; does not change running connections.

Use --enable only after reviewing the generated connection selection design.
Default installation leaves new routing choices unavailable to the API.
"""
import base64
import fcntl
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PAYLOAD = ''  # Embedded by build-update.py
SHA256 = ''
ROOT_DISPATCH = '''
# TOLF Windows routing dispatch v1
if [ "${1:-}" = windows-routing ]; then
    shift
    exec /usr/bin/python3 /usr/local/lib/tolf-windows-routing.py "$@"
fi
'''
SSH_DISPATCH = '''
# TOLF Windows routing dispatch v1
TOLF_WIN_UUID='[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
TOLF_WIN_PATTERN="^windows-routing (capabilities|remove $TOLF_WIN_UUID|apply $TOLF_WIN_UUID (riga|moscow) (sr|ru|lv|default))$"
if [[ "${SSH_ORIGINAL_COMMAND:-}" =~ $TOLF_WIN_PATTERN ]]; then
    read -r -a TOLF_WIN_ARGS <<< "$SSH_ORIGINAL_COMMAND"
    exec sudo -n /usr/local/sbin/tolf-provision-root "${TOLF_WIN_ARGS[@]}"
fi
'''


def main():
    if sys.argv[1:] not in ([], ['--enable']): raise RuntimeError('Use no arguments or --enable')
    if os.geteuid() != 0: raise RuntimeError('Run on Riga as root')
    data = base64.b64decode(PAYLOAD) if PAYLOAD else Path(__file__).with_name('routing-control.py').read_bytes()
    if PAYLOAD and hashlib.sha256(data).hexdigest() != SHA256: raise RuntimeError('Controller checksum mismatch')
    compile(data, 'routing-control.py', 'exec')
    files = {}
    for path, addition in [('/usr/local/sbin/tolf-provision-root', ROOT_DISPATCH), ('/usr/local/sbin/tolf-provision-ssh', SSH_DISPATCH)]:
        p = Path(path); original = p.read_text()
        if addition in original: files[p] = p.read_bytes(); continue
        if 'TOLF Windows routing dispatch' in original: raise RuntimeError('Unknown existing dispatch version')
        anchor = 'set -euo pipefail\n'
        if not original.startswith('#!/bin/bash\n') or original.count(anchor) != 1:
            raise RuntimeError('Unsupported provisioning wrapper; nothing changed')
        updated = original.replace(anchor, anchor+addition, 1)
        subprocess.run(['bash', '-n'], input=updated, text=True, check=True)
        files[p] = updated.encode()
    target = Path('/usr/local/lib/tolf-windows-routing.py')
    target.parent.mkdir(parents=True, exist_ok=True)
    files[target] = data
    backup = Path(tempfile.mkdtemp(prefix='tolf-windows-routing-backup-', dir='/root'))
    originals = {p: p.read_bytes() if p.exists() else None for p in files}
    modes = {p: p.stat().st_mode & 0o777 if p.exists() else 0o700 for p in files}
    for p, value in originals.items():
        if value is not None: (backup/p.name).write_bytes(value)
    print('Backup:', backup, flush=True)
    state = Path('/var/lib/ike-users/windows-routing')
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    was_enabled = (state/'enabled').exists()
    try:
        for p, value in files.items():
            fd, temporary = tempfile.mkstemp(dir=p.parent)
            with os.fdopen(fd, 'wb') as f:
                os.fchmod(f.fileno(), modes[p]); f.write(value); f.flush(); os.fsync(f.fileno())
            os.replace(temporary, p)
        # Import the installed controller only for its read-only preflight.
        spec = importlib.util.spec_from_file_location('routing_control', target)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        for node in module.HOSTS: module.preflight(node)
        if '--enable' in sys.argv: (state/'enabled').touch(mode=0o600)
    except Exception:
        for p,value in originals.items():
            if value is None: p.unlink(missing_ok=True)
            else: p.write_bytes(value); p.chmod(modes[p])
        if not was_enabled: (state/'enabled').unlink(missing_ok=True)
        raise
    print('OK: Windows routing controller installed on Riga; existing VPN connections unchanged.')
    print('New routing choices are '+('enabled; test a new Windows device before wider use.' if (state/'enabled').exists() else 'disabled.'))


if __name__ == '__main__':
    with open('/var/lock/tolf-windows-routing-install.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
