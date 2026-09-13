#!/usr/bin/python3
"""Root-only invitation issuer and UUID -> existing EAP user registry."""
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import sqlite3
import sys
import time
import uuid

ROOT = Path('/var/lib/ike-users/web-bindings')
CREDS = Path('/etc/swanctl/conf.d')
LOCK = Path('/var/lock/tolf-provision.lock')
PROTECTED = {'user0', 'user0_ipad'}
TOKEN = re.compile(r'[A-Za-z0-9_-]{43}')
NAME = re.compile(r'[A-Za-z0-9_.@-]{1,128}')

class Rejected(Exception):
    pass

def database():
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    ROOT.chmod(0o700)
    con = sqlite3.connect(ROOT / 'bindings.db', timeout=30)
    con.executescript('''
        CREATE TABLE IF NOT EXISTS bindings (
          account TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS invitations (
          digest TEXT PRIMARY KEY, username TEXT NOT NULL, expires REAL NOT NULL,
          claimed_by TEXT, revoked INTEGER NOT NULL DEFAULT 0);
    ''')
    columns = {row[1] for row in con.execute('PRAGMA table_info(invitations)')}
    if 'proof' not in columns:
        con.execute('ALTER TABLE invitations ADD COLUMN proof TEXT')
        con.commit()
    con.execute('CREATE TABLE IF NOT EXISTS attempts (key TEXT PRIMARY KEY, started REAL, count INTEGER)')
    con.commit()
    return con

def account_id(value):
    result = str(uuid.UUID(value))
    if value != result:
        raise Rejected('invalid_account')
    return result

def credential_exists(username):
    if not NAME.fullmatch(username):
        raise Rejected('invalid_username')
    path = CREDS / ('user-' + username + '.conf')
    if path.is_symlink() or not path.is_file():
        raise Rejected('user_not_found')
    # Confirm the EAP identity, without returning or modifying its secret.
    text = path.read_text()
    ids = re.findall(r'^\s*id\s*=\s*([^\n]+?)\s*$', text, re.M)
    if [shlex.split(value) for value in ids] != [[username]] or len(re.findall(r'^\s*secret\s*=', text, re.M)) != 1:
        raise Rejected('unsupported_credential_file')

def password_proof(username):
    credential_exists(username)
    text = (CREDS / ('user-' + username + '.conf')).read_text()
    matches = re.findall(r'^\s*secret = "(.*)"[ \t]*$', text, re.M)
    if len(matches) != 1:
        raise Rejected('unsupported_credential_file')
    return matches[0]


def proof_digest(username, password):
    key_path = ROOT / 'proof.key'
    if not key_path.exists():
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as output:
            output.write(secrets.token_bytes(32))
            output.flush()
            os.fsync(output.fileno())
    return hmac.new(key_path.read_bytes(), (username+'\0'+password).encode(), hashlib.sha256).hexdigest()


def throttle(con, key, maximum):
    now = time.time()
    with con:
        con.execute('DELETE FROM attempts WHERE started<?', (now-900,))
        row = con.execute('SELECT count FROM attempts WHERE key=?', (key,)).fetchone()
        if row and row[0] >= maximum:
            raise Rejected('too_many_attempts')
        con.execute('INSERT INTO attempts VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET count=count+1', (key,now))


def verify_existing(con, payload):
    throttle(con, 'global', 200)
    username = payload.get('username')
    password = payload.get('password')
    if not isinstance(username,str) or not NAME.fullmatch(username) or not isinstance(password,str) or not 1<=len(password)<=256:
        raise Rejected('invalid_credentials')
    throttle(con, hashlib.sha256(username.encode()).hexdigest(), 10)
    if username in PROTECTED:
        raise Rejected('admin_invitation_required')
    if re.fullmatch(r'(?:user|u)_[0-9a-fA-F]{32}', username):
        raise Rejected('invalid_credentials')
    try:
        actual = password_proof(username)
    except (Rejected, ValueError):
        actual = secrets.token_urlsafe(32)
        known = False
    else:
        known = True
    valid = hmac.compare_digest(actual.encode(), password.encode())
    if not valid or not known:
        raise Rejected('invalid_credentials')
    bound = con.execute('SELECT account FROM bindings WHERE username=?', (username,)).fetchone()
    retry_owner = bound[0] if bound else None
    if bound and payload.get('retryAccount') != retry_owner:
        raise Rejected('already_linked')
    token = secrets.token_urlsafe(32)
    with con:
        con.execute('INSERT INTO invitations(digest,username,expires,proof,claimed_by) VALUES(?,?,?,?,?)',
                    (hashlib.sha256(token.encode()).hexdigest(),username,time.time()+900,proof_digest(username,actual),retry_owner))
    return {'status':'ok','token':token,'username':username,'expiresIn':900}


def issue(con, username):
    credential_exists(username)
    if re.fullmatch(r'(?:user|u)_[0-9a-fA-F]{32}', username):
        raise Rejected('website_managed_user')
    if con.execute('SELECT 1 FROM bindings WHERE username=?', (username,)).fetchone():
        raise Rejected('already_linked')
    token = secrets.token_urlsafe(32)
    with con:
        con.execute('UPDATE invitations SET revoked=1 WHERE username=? AND claimed_by IS NULL', (username,))
        con.execute('INSERT INTO invitations(digest,username,expires) VALUES(?,?,?)',
                    (hashlib.sha256(token.encode()).hexdigest(), username, time.time()+86400))
    return 'https://vpn.tolf.is/#invite=' + token

def claim(con, account, token):
    account_id(account)
    if not TOKEN.fullmatch(token):
        raise Rejected('invalid_invitation')
    digest = hashlib.sha256(token.encode()).hexdigest()
    with con:
        row = con.execute('SELECT username,expires,claimed_by,revoked,proof FROM invitations WHERE digest=?', (digest,)).fetchone()
        if not row or row[3]:
            raise Rejected('invalid_invitation')
        username, expires, owner, _, proof = row
        if owner and owner != account:
            raise Rejected('invitation_used')
        if (not owner or proof) and expires <= time.time():
            raise Rejected('invitation_expired')
        credential_exists(username)
        if proof:
            if username in PROTECTED:
                raise Rejected('admin_invitation_required')
            if not hmac.compare_digest(proof, proof_digest(username, password_proof(username))):
                raise Rejected('invalid_invitation')
        current = con.execute('SELECT username FROM bindings WHERE account=?', (account,)).fetchone()
        other = con.execute('SELECT account FROM bindings WHERE username=?', (username,)).fetchone()
        if (current and current[0] != username) or (other and other[0] != account):
            raise Rejected('already_linked')
        if not current:
            compact = account.replace('-', '')
            if any((CREDS / ('user-' + prefix + compact + '.conf')).exists() for prefix in ('user_', 'u_')):
                raise Rejected('account_has_vpn')
            con.execute('INSERT INTO bindings VALUES(?,?,?)', (account, username, time.time()))
        con.execute('UPDATE invitations SET claimed_by=? WHERE digest=?', (account, digest))
    return {'status':'ok', 'username':username, 'protected':username in PROTECTED}

def run(args):
    if os.geteuid() != 0:
        raise Rejected('root_required')
    os.umask(0o077)
    if len(args) == 2 and args[0] in ('resolve', 'release'):
        # The provisioner already holds LOCK; do not try to acquire it again.
        account_id(args[1])
        with database() as con:
            row = con.execute('SELECT username FROM bindings WHERE account=?', (args[1],)).fetchone()
            if args[0] == 'release' and row:
                if (CREDS / ('user-' + row[0] + '.conf')).exists():
                    return
                with con:
                    con.execute('UPDATE invitations SET revoked=1 WHERE claimed_by=?', (args[1],))
                    con.execute('DELETE FROM bindings WHERE account=?', (args[1],))
        if args[0] == 'resolve': print(row[0] if row else '')
        return
    with LOCK.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with database() as con:
            if args == ['verify-existing']:
                raw = sys.stdin.buffer.read(4097)
                if len(raw)>4096: raise Rejected('invalid_credentials')
                try: payload = json.loads(raw)
                except (ValueError, UnicodeError): raise Rejected('invalid_credentials')
                if not isinstance(payload,dict): raise Rejected('invalid_credentials')
                print(json.dumps(verify_existing(con,payload)))
            elif len(args) == 2 and args[0] == 'issue':
                print(issue(con, args[1]))
            elif len(args) == 2 and args[0] == 'revoke':
                if not NAME.fullmatch(args[1]): raise Rejected('invalid_username')
                with con:
                    con.execute('UPDATE invitations SET revoked=1 WHERE username=? AND claimed_by IS NULL', (args[1],))
                print('OK: unused invitations revoked')
            elif len(args) == 3 and args[0] == 'claim-existing':
                print(json.dumps(claim(con, args[1], args[2])))
            else:
                raise Rejected('invalid_arguments')

if __name__ == '__main__':
    try:
        run(sys.argv[1:])
    except (Rejected, ValueError) as exc:
        print(json.dumps({'status':'error','code':str(exc),'error':'Existing VPN account could not be linked'}))
        sys.exit(1)
