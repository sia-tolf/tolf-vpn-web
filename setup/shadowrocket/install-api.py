#!/usr/bin/env python3
"""Update only the reviewed password API functions; never alter VPN services or account data."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

EXPECTED_LIVE_SHA256 = '2885afbf428fc7717b1ee1a581d8994f8a8380d7054c8bcefa3ae3369c63be66'
REPLACEMENTS = {'capabilities': "    def capabilities():\n        return JSONResponse({'version':VERSION, 'accountManagement':True, 'verifyAccountPassword':True,\n                             'createOnly':True, 'minPasswordLength':15, 'maxPasswordLength':128}, headers=HEADERS)\n", 'set_password': "    def set_password(request: Request, payload: dict):\n        uid = ns['authenticated_user_id'](request)\n        guard(request, 'set', uid)\n        value = password(payload.get('password'))\n        with db() as con:\n            existing = con.execute('SELECT username FROM account_passwords WHERE user_id=?', (uid,)).fetchone()\n        if payload.get('createOnly') is True and existing:\n            raise HTTPException(409, 'account_password_exists')\n        name = existing[0] if existing else username(payload.get('username'))\n        salt = secrets.token_bytes(16)\n        digest = derive(value, salt)\n        with db() as con:\n            con.execute('BEGIN IMMEDIATE')\n            # Recheck the exact session after hashing: recovery/logout may have revoked it.\n            token = request.cookies.get(ns['SESSION_COOKIE'], '')\n            valid = con.execute('SELECT 1 FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.user_id=? AND s.token_hash=? AND s.expires_at>?',\n                                (uid, hashlib.sha256(token.encode()).digest(), ns['utc_iso'](ns['utc_now']()))).fetchone()\n            if not valid:\n                raise HTTPException(401, 'authentication_required')\n            current = con.execute('SELECT username FROM account_passwords WHERE user_id=?', (uid,)).fetchone()\n            if payload.get('createOnly') is True and current:\n                raise HTTPException(409, 'account_password_exists')\n            if current:\n                name = current[0]\n                con.execute('UPDATE account_passwords SET salt=?,digest=? WHERE user_id=?', (salt,digest,uid))\n            else:\n                if con.execute('SELECT 1 FROM account_passwords WHERE username=?', (name,)).fetchone():\n                    raise HTTPException(409, 'username_taken')\n                con.execute('INSERT INTO account_passwords VALUES (?,?,?,?,?)', (uid,name,salt,digest,ns['utc_iso'](ns['utc_now']())))\n            con.execute('DELETE FROM sessions WHERE user_id=?', (uid,))\n            con.execute('DELETE FROM challenges WHERE user_id=?', (uid,))\n            response = session(con, uid, {'username':name})\n        return response\n"}
VERIFY = "    @app.post('/password/verify')\n    def verify_account_password(request: Request, payload: dict):\n        uid = ns['authenticated_user_id'](request)\n        with db() as con:\n            row = con.execute('SELECT username,salt,digest FROM account_passwords WHERE user_id=?', (uid,)).fetchone()\n        guard(request, 'login', row[0] if row else uid)\n        value = payload.get('password')\n        if not isinstance(value, str) or not 1 <= len(value) <= 128 or len(value.encode('utf-8')) > 512:\n            raise HTTPException(401, 'invalid_credentials')\n        candidate = derive(value, row[1] if row else b'TOLF-dummy-salt!')\n        if not row or not hmac.compare_digest(candidate, row[2]):\n            raise HTTPException(401, 'invalid_credentials')\n        with db() as con:\n            # Verification never issues a login cookie or changes the account password.\n            token = request.cookies.get(ns['SESSION_COOKIE'], '')\n            current = con.execute('''SELECT p.digest FROM account_passwords p\n                JOIN users u ON u.id=p.user_id JOIN sessions s ON s.user_id=u.id\n                WHERE u.id=? AND s.token_hash=? AND s.expires_at>?''',\n                (uid, hashlib.sha256(token.encode()).digest(), ns['utc_iso'](ns['utc_now']()))).fetchone()\n            if not current or not hmac.compare_digest(current[0], row[2]):\n                raise HTTPException(401, 'authentication_required')\n        return JSONResponse({'username':row[0]}, headers=HEADERS)\n"

def plan(source, expected_hash=EXPECTED_LIVE_SHA256):
    if hashlib.sha256(source.encode()).hexdigest() != expected_hash:
        raise RuntimeError('Password API changed since review; no files modified')
    tree=ast.parse(source)
    install=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='install')
    functions={n.name:n for n in install.body if isinstance(n,ast.FunctionDef)}
    if 'verify_account_password' in functions:
        raise RuntimeError('Verification handler already exists')
    lines=source.splitlines(keepends=True)
    lines.insert(install.end_lineno, '\n'+VERIFY)
    for name in sorted(REPLACEMENTS,key=lambda key:functions[key].lineno,reverse=True):
        node=functions[name]
        lines[node.lineno-1:node.end_lineno]=[REPLACEMENTS[name]]
    result=''.join(lines)
    compile(result,'tolf_password_auth.py','exec')
    return result


def main():
    apply=sys.argv[1:]==['--apply']
    if not apply and sys.argv[1:]!=['--check']:
        raise SystemExit('Use --check or --apply')
    target=Path('/opt/tolf-api/tolf_password_auth.py')
    original=target.read_bytes()
    candidate=plan(original.decode())
    print(json.dumps({'checked':True,'originalSha256':hashlib.sha256(original).hexdigest(),
                      'candidateSha256':hashlib.sha256(candidate.encode()).hexdigest()}),flush=True)
    if not apply:return
    backup=Path(tempfile.mkdtemp(prefix='shadowrocket-api-backup-',dir=target.parent))
    backup.chmod(0o700);shutil.copy2(target,backup/target.name)
    info=target.stat()
    def write(value):
        fd,name=tempfile.mkstemp(prefix='.shadowrocket-',dir=target.parent)
        try:
            with os.fdopen(fd,'wb') as f:f.write(value);f.flush();os.fsync(f.fileno())
            os.chown(name,info.st_uid,info.st_gid);os.chmod(name,info.st_mode&0o777)
            os.replace(name,target)
        finally:
            if os.path.exists(name):os.unlink(name)
    installed=False
    try:
        # Recheck immediately before replacement, without changing user records.
        if target.read_bytes()!=original:raise RuntimeError('Concurrent API edit')
        write(candidate.encode())
        installed=True
        subprocess.run(['systemctl','restart','tolf-api.service'],check=True,timeout=40)
        for attempt in range(6):
            try:
                with urllib.request.urlopen('https://api.tolf.is/password/capabilities',timeout=5) as r:data=json.load(r)
                if data.get('verifyAccountPassword') is not True or data.get('createOnly') is not True:
                    raise RuntimeError('Updated API capabilities not served')
                subprocess.run(['systemctl','is-active','--quiet','tolf-api.service'],check=True)
                break
            except Exception:
                if attempt==5:raise
                time.sleep(1)
    except Exception:
        if installed:
            if target.read_bytes()!=candidate.encode():
                raise RuntimeError('API changed after installation; refusing to overwrite a concurrent edit')
            write(original)
            subprocess.run(['systemctl','restart','tolf-api.service'],check=False,timeout=40)
        raise
    print(json.dumps({'installed':True,'backup':str(backup),'service':'tolf-api.service'}))

if __name__=='__main__':main()
