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
