#!/usr/bin/env python3
"""Install the read-only TOLF admin inventory on London; grant roles only as root."""
import argparse
import ast
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.request
import fcntl

PAYLOAD = ''  # Filled by build.py
PAYLOAD_SHA256 = ''
ROOT = Path('/opt/tolf-api')
DB = '/var/lib/tolf-api/tolf.db'
MARKER = '# TOLF admin inventory v1'


def patch(source):
    tree = ast.parse(source)
    names = {n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    if 'authenticated_user_id' not in names:
        raise RuntimeError('Expected authentication function is missing; nothing changed')
    if MARKER in source:
        if 'tolf_admin.install(app, globals())' not in source:
            raise RuntimeError('Admin integration differs; nothing changed')
        return source
    addition = '\n'+MARKER+'\nimport tolf_admin\ntolf_admin.install(app, globals())\n'
    lines = source.splitlines(keepends=True)
    for node in tree.body:
        if isinstance(node,ast.If) and '__name__' in ast.unparse(node.test) and '__main__' in ast.unparse(node.test):
            index = node.lineno-1
            return ''.join(lines[:index])+addition+'\n'+''.join(lines[index:])
    return source.rstrip()+'\n'+addition


def module():
    spec = importlib.util.spec_from_file_location('tolf_admin_installer',ROOT/'tolf_admin.py')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def inventory():
    with sqlite3.connect('file:'+DB+'?mode=ro',uri=True) as con:
        rows = con.execute('SELECT m.number,m.vpn_username,u.id FROM managed_users m JOIN users u ON u.id=m.account_id WHERE m.deleted_at IS NULL ORDER BY m.number').fetchall()
        for number,username,user_id in rows:
            names = [r[0] for r in con.execute('SELECT name FROM passkeys WHERE user_id=? ORDER BY created_at',(user_id,)) if r[0]]
            # JSON escaping prevents control characters in user labels affecting the terminal.
            print(json.dumps({'number':number,'vpn':username,'passkeys':names},ensure_ascii=True))
        return rows


def atomic(path,data,info):
    fd,temp = tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        os.chown(temp,info.st_uid,info.st_gid);os.chmod(temp,info.st_mode & 0o777)
        os.replace(temp,path)
    finally:
        Path(temp).unlink(missing_ok=True)


def install():
    path=ROOT/'main.py';target=ROOT/'tolf_admin.py'
    source=path.read_text();original=path.read_bytes();updated=patch(source)
    data=base64.b64decode(PAYLOAD)
    if hashlib.sha256(data).hexdigest()!=PAYLOAD_SHA256:
        raise RuntimeError('Admin payload checksum mismatch')
    compile(data,str(target),'exec');compile(updated,str(path),'exec')
    with sqlite3.connect('file:'+DB+'?mode=ro',uri=True) as con:
        required={'users':{'id','created_at'},'managed_users':{'number','account_id','vpn_username','created_at','source','vpn_active','deleted_at'},'vpn_access':{'user_id','vpn_username','created_at','server'},'passkeys':{'user_id','name','created_at'},'vpn_imports':{'user_id','protected'},'windows_devices':{'id','user_id','name','username','state','created_at'},'windows_device_nodes':{'device_id','server'}}
        for table,columns in required.items():
            actual={r[1] for r in con.execute('PRAGMA table_info('+table+')')}
            if not columns.issubset(actual):raise RuntimeError('Unsupported database schema: '+table)
    backup=Path('/root/tolf-admin-backup-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid()));backup.mkdir(mode=0o700)
    shutil.copy2(path,backup/'main.py')
    if target.exists():shutil.copy2(target,backup/'tolf_admin.py')
    info=path.stat()
    print('Backup:',backup,flush=True)
    if path.read_bytes()!=original:raise RuntimeError('API source changed during preparation; nothing changed')
    try:
        atomic(target,data,info);atomic(path,updated.encode(),info)
        subprocess.run(['systemctl','restart','tolf-api.service'],check=True)
        for _ in range(12):
            try:
                with urllib.request.urlopen('https://api.tolf.is/admin/capabilities',timeout=5) as r:status=json.load(r)
                if status.get('version')=='1.2.0' and status.get('testDisconnect') is True and status.get('sessions') is True and status.get('inventory') is True:
                    print('OK: TOLF admin 1.2 API enabled; disconnect restricted to Test #26. VPN sessions and credentials were not changed.',flush=True)
                    return
            except Exception:pass
            time.sleep(1)
        raise RuntimeError('Admin API did not pass its availability check')
    except Exception:
        atomic(path,(backup/'main.py').read_bytes(),info)
        if (backup/'tolf_admin.py').exists():atomic(target,(backup/'tolf_admin.py').read_bytes(),info)
        else:target.unlink(missing_ok=True)
        subprocess.run(['systemctl','restart','tolf-api.service'],check=False)
        print('Previous API files restored; backup:',backup)
        raise


def main():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--grant-number',type=int)
    group.add_argument('--revoke-number',type=int)
    group.add_argument('--list-accounts',action='store_true')
    args=parser.parse_args()
    if os.geteuid()!=0 or not (ROOT/'main.py').is_file():raise SystemExit('Run as root on London EDISUK')
    import sys
    with open('/run/lock/tolf-admin-install.lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if args.list_accounts:inventory();return
        if args.grant_number is not None:
            value=module().root_grant(DB,args.grant_number);print('Administrator granted to account:',args.grant_number,value);return
        if args.revoke_number is not None:
            value=module().root_revoke(DB,args.revoke_number);print('Administrator revoked:',args.revoke_number,value);return
        install()
        with sqlite3.connect(DB) as con:
            has_admin=con.execute('SELECT 1 FROM admin_roles a JOIN users u ON u.id=a.user_id LIMIT 1').fetchone()
        if not has_admin and sys.stdin.isatty():
            print('\nSelect YOUR account using its number and Passkey names:')
            inventory()
            chosen=input('Administrator account number (Enter to skip): ').strip()
            if chosen:
                if not chosen.isdecimal():raise SystemExit('Not a number. API installed; no administrator assigned.')
                module().root_grant(DB,int(chosen));print('Administrator granted to account:',chosen)
        print('Open https://vpn.tolf.is/admin/ after signing in with your Passkey.')
        if not has_admin:print('You can also assign access later: python3 '+str(Path(__file__).resolve())+' --grant-number NUMBER')

if __name__=='__main__':main()
