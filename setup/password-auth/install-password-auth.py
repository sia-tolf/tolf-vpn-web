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
