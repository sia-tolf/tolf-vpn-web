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
