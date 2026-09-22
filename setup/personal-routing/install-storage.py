#!/usr/bin/env python3
"""Install UK storage only. Existing VPN routes/profiles are not modified."""
import hashlib
import importlib.util
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

MODULE_SHA256 = '8b750e1af746ce863e99000ea5d48f5bdf7aec08fc7427489375a9d0acd932d9'
MARKER = '# TOLF personal routing storage v1'
SUFFIX = '\n\n' + MARKER + '\nimport tolf_personal_routing\ntolf_personal_routing.install(app, globals())\n'
ROOT = Path('/opt/tolf-api')
DB = Path('/var/lib/tolf-api/tolf.db')
MODULE_NAME = 'tolf_personal_routing.py'


def patched_main(original):
    if 'tolf_personal_routing' in original:
        raise RuntimeError('Routing integration already exists; refusing to overwrite it')
    for anchor in ('def authenticated_user_id(', 'import tolf_promos', 'app = FastAPI('):
        if anchor not in original:
            raise RuntimeError('Unexpected main.py structure: ' + anchor)
    updated = original.rstrip() + SUFFIX
    compile(updated, 'main.py', 'exec')
    return updated


def replace(path, content, mode, uid, gid):
    fd, name = tempfile.mkstemp(prefix='.routing-stage-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, mode)
        os.chown(name, uid, gid)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def status(path):
    # No proxy or cookies; probe only the local API.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open('http://127.0.0.1:8000' + path, timeout=2) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def wait_api(expect_routing):
    for _ in range(10):
        try:
            if status('/health') == 200 and (not expect_routing or status('/vpn/routing-rules') == 401):
                return
        except OSError:
            pass
        time.sleep(0.5)
    raise RuntimeError('API health/authentication check failed')


def main():
    if os.geteuid() != 0 or socket.gethostname().split('.')[0] != 'EDISUK':
        raise RuntimeError('Run as root on EDISUK only')
    source = Path(__file__).resolve().with_name(MODULE_NAME)
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != MODULE_SHA256:
        raise RuntimeError('Module checksum mismatch')
    compile(data, MODULE_NAME, 'exec')
    target = ROOT / MODULE_NAME
    entry = ROOT / 'main.py'
    if target.exists() or target.is_symlink() or entry.is_symlink():
        raise RuntimeError('Module already exists or unexpected symlink; no changes made')
    before = entry.read_bytes()
    after = patched_main(before.decode('utf-8')).encode('utf-8')
    info = entry.stat()
    subprocess.run(['systemctl', 'is-active', '--quiet', 'tolf-api'], check=True)
    wait_api(False)
    # Verify the actual database without creating one at an incorrect path.
    con = sqlite3.connect(DB.as_uri() + '?mode=ro', uri=True)
    try:
        con.execute('SELECT id FROM users LIMIT 0')
        con.execute('SELECT user_id,vpn_username FROM vpn_access LIMIT 0')
        if con.execute("SELECT 1 FROM sqlite_master WHERE name='vpn_personal_routing'").fetchone():
            raise RuntimeError('Routing table already exists; inspect before retrying')
        backup = Path(tempfile.mkdtemp(prefix='routing-install-backup-', dir=ROOT))
        shutil.copy2(entry, backup / 'main.py')
        dest = sqlite3.connect(str(backup / 'tolf.db'))
        try:
            con.backup(dest)
        finally:
            dest.close()
    finally:
        con.close()
    print('Backup:', backup, flush=True)
    if entry.read_bytes() != before or target.exists():
        raise RuntimeError('Files changed during preparation; installation cancelled')
    try:
        replace(target, data, 0o644, info.st_uid, info.st_gid)
        # Check schema creation before restarting, using the installed module only.
        spec = importlib.util.spec_from_file_location('routing_install_check', target)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.initialize(str(DB))
        replace(entry, after, info.st_mode & 0o777, info.st_uid, info.st_gid)
        subprocess.run(['systemctl', 'restart', 'tolf-api'], check=True, timeout=30)
        wait_api(True)
    except Exception:
        # Do not restore the whole live database: other accounts may have changed.
        replace(entry, before, info.st_mode & 0o777, info.st_uid, info.st_gid)
        if target.exists() and target.read_bytes() == data:
            target.unlink()
        try:
            subprocess.run(['systemctl', 'restart', 'tolf-api'], check=True, timeout=30)
            wait_api(False)
            print('Code rolled back; API healthy. Any new storage table is retained.', flush=True)
        except Exception:
            print('ROLLBACK NEEDS ATTENTION. Backup:', backup, flush=True)
        raise
    print('OK: personal routing STORAGE installed; enforcement remains OFF.')
    print('OK: /health = 200; unauthenticated /vpn/routing-rules = 401.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(1)
