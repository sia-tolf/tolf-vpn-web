#!/usr/bin/env python3
"""Install TOLF Windows API v1 on the existing London API node only."""
import ast
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.request
import zlib

PAYLOADS = {'tolf_windows.py': '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', 'tolf-windows-install.ps1': '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'}
MARKER = '# TOLF Windows devices v1'


def patch_main(source):
    if MARKER in source:
        raise RuntimeError('Windows API already installed; refusing an unreviewed overwrite')
    parsed = ast.parse(source)
    functions = {node.name: node for node in parsed.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for name in ('authenticated_user_id', 'provision_on_riga', 'remove_provisioned_vpn', 'account_delete', 'requested_platform'):
        if name not in functions:
            raise RuntimeError('Unexpected API source: missing ' + name)
    node = functions['account_delete']
    lines = source.splitlines(keepends=True)
    old = ''.join(lines[node.lineno-1:node.end_lineno])
    anchor = '        row = vpn_record(user_id)\n'
    tables = 'for table in ("vpn_access", "passkeys", "sessions"):'
    if old.count(anchor) != 1 or old.count(tables) != 1 or 'with tolf_promos.account_operation(DB, user_id):' not in old:
        raise RuntimeError('Unexpected account deletion handler; nothing changed')
    new = old.replace(anchor, '        tolf_windows.delete_all(user_id)\n' + anchor).replace(tables, 'for table in ("windows_devices", "vpn_access", "passkeys", "sessions"):')
    lines[node.lineno-1:node.end_lineno] = [new]
    result = ''.join(lines).rstrip() + '\n\n' + MARKER + '\nimport tolf_windows\ntolf_windows.install(app, globals())\n'
    compile(result, 'main.py', 'exec')
    return result


def atomic(path, content, info):
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.windows-install-')
    try:
        with os.fdopen(fd, 'wb') as f:
            os.fchmod(f.fileno(), info.st_mode & 0o777)
            os.fchown(f.fileno(), info.st_uid, info.st_gid)
            f.write(content); f.flush(); os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def main():
    if os.geteuid() != 0: raise RuntimeError('Run as root on EDISUK')
    root = Path('/opt/tolf-api'); path = root/'main.py'
    if not path.is_file() or not (root/'tolf_profiles.py').is_file():
        raise RuntimeError('This is not the London API node')
    subprocess.run(['systemctl', 'is-active', '--quiet', 'tolf-api.service'], check=True)
    source = path.read_text(); patched = patch_main(source)
    payloads = {name:zlib.decompress(base64.b64decode(data)) for name,data in PAYLOADS.items()}
    for name, data in payloads.items():
        if (root/name).exists(): raise RuntimeError(name + ' already exists; nothing changed')
        if name.endswith('.py'): compile(data, name, 'exec')
    backup = Path('/root')/('tolf-windows-backup-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid()))
    backup.mkdir(mode=0o700)
    shutil.copy2(path, backup/'main.py')
    # Consistent SQLite snapshot; never restore over newer user changes automatically.
    src = sqlite3.connect('/var/lib/tolf-api/tolf.db'); dst=sqlite3.connect(backup/'tolf.db')
    try: src.backup(dst)
    finally: src.close();dst.close()
    print('Backup:', backup, flush=True)
    info=path.stat(); written=[]
    try:
        if path.read_text()!=source: raise RuntimeError('API source changed during preparation')
        for name,data in payloads.items():
            atomic(root/name,data,info);written.append(root/name)
        atomic(path,patched.encode(),info)
        subprocess.run(['systemctl','restart','tolf-api.service'],check=True)
        for attempt in range(12):
            try:
                with urllib.request.urlopen('https://api.tolf.is/windows/capabilities', timeout=5) as r:
                    result=json.load(r)
                if result.get('version')=='1.0' and result.get('servers')==['riga']:
                    print('OK: Windows API v1 installed; Riga enabled. Existing Apple/Android access retained.')
                    return
            except Exception:
                pass
            time.sleep(2)
        raise RuntimeError('Windows API health check failed')
    except Exception:
        atomic(path,source.encode(),info)
        for p in written: p.unlink(missing_ok=True)
        subprocess.run(['systemctl','restart','tolf-api.service'],check=False)
        print('Original API files restored. Backup:',backup,flush=True)
        raise


if __name__=='__main__':
    with open('/var/lock/tolf-windows-install.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        main()
