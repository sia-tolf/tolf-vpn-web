#!/usr/bin/env python3
"""Install additive password authentication on London; keep existing API handlers."""
import ast
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import time
import urllib.request
import zlib

PAYLOAD = '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'
MARKER = '# TOLF password authentication v1'


def patch(source):
    tree = ast.parse(source)
    names = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if not {'authenticated_user_id','generate_recovery_code','recovery_code_hash','passkey_register_finish'} <= names:
        raise RuntimeError('Unrecognized account API; nothing changed')
    if MARKER in source:
        return source
    result = source + '\n'+MARKER+'\nimport tolf_password_auth\ntolf_password_auth.install(app, globals())\n'
    compile(result,'main.py','exec')
    return result


def main():
    if os.geteuid()!=0 or socket.gethostname()!='EDISUK':
        raise SystemExit('Run as root on London (EDISUK)')
    root=Path('/opt/tolf-api'); first=root/'main.py'
    with open('/var/lock/tolf-password-install.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        original=first.read_text(); modified=patch(original)
        module=zlib.decompress(base64.b64decode(PAYLOAD)).decode()
        compile(module,'tolf_password_auth.py','exec')
        # Test real schema compatibility read-only before changing files.
        tree=ast.parse(original)
        dbs=[ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DB' for t in n.targets)]
        if len(dbs)!=1 or not Path(dbs[0]).is_file():
            raise RuntimeError('Cannot locate account database; nothing changed')
        con=sqlite3.connect('file:'+dbs[0]+'?mode=ro',uri=True)
        try:
            required={'users':{'id','created_at','webauthn_user_id','recovery_code_hash'},'sessions':{'token_hash','user_id','created_at','expires_at'},'challenges':{'user_id','webauthn_user_id'}}
            for table,columns in required.items():
                if not columns <= {r[1] for r in con.execute('PRAGMA table_info('+table+')')}:
                    raise RuntimeError('Unsupported schema: '+table)
        finally:
            con.close()
        backup=Path(tempfile.mkdtemp(prefix='tolf-password-backup-',dir='/root'))
        targets={first:modified,root/'tolf_password_auth.py':module}
        existed={p:p.exists() for p in targets}
        for p in targets:
            if p.exists():shutil.copy2(p,backup/p.name)
        # Online backup provides a consistent snapshot even when WAL is enabled.
        with sqlite3.connect('file:'+dbs[0]+'?mode=ro',uri=True) as source, sqlite3.connect(backup/'tolf.db') as dest:
            source.backup(dest)
        os.chmod(backup/'tolf.db',0o600)
        print('Backup:',backup,flush=True)
        owner=first.stat()
        def write(path,value):
            fd,name=tempfile.mkstemp(dir=root,prefix='.password-')
            try:
                with os.fdopen(fd,'w') as f:f.write(value);f.flush();os.fsync(f.fileno())
                os.chown(name,owner.st_uid,owner.st_gid);os.chmod(name,owner.st_mode & 0o777)
                os.replace(name,path)
            finally:
                if os.path.exists(name):os.unlink(name)
        try:
            for p,value in targets.items():write(p,value)
            subprocess.run(['systemctl','restart','tolf-api.service'],check=True,timeout=40)
            for attempt in range(8):
                try:
                    with urllib.request.urlopen('https://api.tolf.is/password/capabilities',timeout=5) as r:data=json.load(r)
                    if data.get('version')!=1:raise RuntimeError('Capabilities mismatch')
                    subprocess.run(['systemctl','is-active','--quiet','tolf-api.service'],check=True)
                    break
                except Exception:
                    if attempt==7:raise
                    time.sleep(1)
        except Exception:
            # Do not roll back the database: that could erase concurrent user work.
            for p in targets:
                if existed[p]:shutil.copy2(backup/p.name,p)
                else:p.unlink(missing_ok=True)
            subprocess.run(['systemctl','restart','tolf-api.service'],check=False,timeout=40)
            raise
    print('OK: password registration, login and recovery enabled.')
    print('Existing account credentials and VPN settings were not changed.')

if __name__=='__main__':main()
