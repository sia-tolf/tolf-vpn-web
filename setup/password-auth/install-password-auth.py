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
                    if data.get('version')!=1 or data.get('accountManagement') is not True:raise RuntimeError('Capabilities mismatch')
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

