"""Optional password credentials for existing TOLF account/session storage."""
import hashlib
import hmac
import re
import secrets
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import timedelta
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

VERSION = 1
N = 131072
KDF_SLOTS = threading.BoundedSemaphore(2)
HEADERS = {'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'}
COMMON = {'passwordpassword', '123456789012345', '1234567890123456', 'qwertyuiopasdfgh', 'password123456789'}


def username(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{2,31}', value):
        raise HTTPException(400, 'invalid_username')
    return value.lower()


def password(value):
    if not isinstance(value, str) or not 15 <= len(value) <= 128 or len(value.encode('utf-8')) > 512 or '\x00' in value:
        raise HTTPException(400, 'invalid_password')
    if value.lower() in COMMON or len(set(value)) < 5:
        raise HTTPException(400, 'weak_password')
    return value


def derive(value, salt):
    if not KDF_SLOTS.acquire(blocking=False):
        raise HTTPException(429, 'try_later', headers={'Retry-After': '5'})
    try:
        return hashlib.scrypt(value.encode('utf-8'), salt=salt, n=N, r=8, p=1, dklen=32, maxmem=256*1024*1024)
    finally:
        KDF_SLOTS.release()


def install(app, ns):
    @contextmanager
    def db():
        con = sqlite3.connect(ns['DB'], timeout=30)
        try:
            with con:
                yield con
        finally:
            con.close()

    with db() as con:
        # Refuse an incompatible server rather than infer its schema.
        for table, required in {
            'users': {'id', 'created_at', 'webauthn_user_id', 'recovery_code_hash'},
            'sessions': {'token_hash', 'user_id', 'created_at', 'expires_at'},
            'challenges': {'user_id', 'webauthn_user_id'},
        }.items():
            if not required <= {r[1] for r in con.execute('PRAGMA table_info('+table+')')}:
                raise RuntimeError('Unsupported TOLF schema: '+table)
        con.execute('''CREATE TABLE IF NOT EXISTS account_passwords (
            user_id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
            salt BLOB NOT NULL, digest BLOB NOT NULL, created_at TEXT NOT NULL)''')
        con.execute('CREATE TABLE IF NOT EXISTS password_attempts (key TEXT PRIMARY KEY, started REAL NOT NULL, count INTEGER NOT NULL)')
        # Existing handlers do not all enable foreign_keys. Cleanup must still run.
        con.execute('''CREATE TRIGGER IF NOT EXISTS password_account_delete AFTER DELETE ON users
            BEGIN DELETE FROM account_passwords WHERE user_id=OLD.id; END''')
    for key in ('utc_now', 'utc_iso', 'SESSION_DAYS', 'SESSION_COOKIE', 'ORIGIN', 'generate_recovery_code', 'recovery_code_hash'):
        if key not in ns:
            raise RuntimeError('Missing TOLF interface: '+key)

    def guard(request, action, login):
        if request.headers.get('origin') != ns['ORIGIN'] or request.headers.get('content-type','').split(';')[0].strip() != 'application/json':
            raise HTTPException(403, 'invalid_origin')
        address = request.client.host if request.client else 'unknown'
        # Persistent, shared across workers. Ignore caller-supplied forwarding headers.
        keys = [(action+':global', 300), (action+':ip:'+hashlib.sha256(address.encode()).hexdigest(), 20),
                (action+':login:'+hashlib.sha256(login.encode()).hexdigest(), 10)]
        now = time.time()
        with db() as con:
            con.execute('BEGIN IMMEDIATE')
            con.execute('DELETE FROM password_attempts WHERE started<?', (now-900,))
            for key, limit in keys:
                row = con.execute('SELECT count FROM password_attempts WHERE key=?', (key,)).fetchone()
                if row and row[0] >= limit:
                    raise HTTPException(429, 'too_many_attempts', headers={'Retry-After':'900'})
            for key, _ in keys:
                con.execute('INSERT INTO password_attempts VALUES (?,?,1) ON CONFLICT(key) DO UPDATE SET count=count+1', (key,now))

    def session(con, uid, data):
        now = ns['utc_now']()
        token = secrets.token_urlsafe(32)
        con.execute('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES (?,?,?,?)',
                    (hashlib.sha256(token.encode()).digest(), uid, ns['utc_iso'](now), ns['utc_iso'](now+timedelta(days=ns['SESSION_DAYS']))))
        response = JSONResponse({'status':'ok', **data}, headers=HEADERS)
        response.set_cookie(key=ns['SESSION_COOKIE'], value=token, max_age=ns['SESSION_DAYS']*86400,
                            httponly=True, secure=True, samesite='lax', path='/')
        return response

    @app.get('/password/capabilities')
    def capabilities():
        return JSONResponse({'version':VERSION, 'minPasswordLength':15, 'maxPasswordLength':128}, headers=HEADERS)

    @app.post('/password/register')
    def register(request: Request, payload: dict):
        login = username(payload.get('username'))
        guard(request, 'register', login)
        value = password(payload.get('password'))
        salt = secrets.token_bytes(16)
        digest = derive(value, salt)
        uid = str(uuid.uuid4())
        code = ns['generate_recovery_code']()
        with db() as con:
            con.execute('BEGIN IMMEDIATE')
            if con.execute('SELECT 1 FROM account_passwords WHERE username=?', (login,)).fetchone():
                raise HTTPException(409, 'username_taken')
            con.execute('INSERT INTO users(id,created_at,webauthn_user_id,recovery_code_hash) VALUES (?,?,?,?)',
                        (uid, ns['utc_iso'](ns['utc_now']()), secrets.token_bytes(32), ns['recovery_code_hash'](code)))
            con.execute('INSERT INTO account_passwords VALUES (?,?,?,?,?)', (uid, login, salt, digest, ns['utc_iso'](ns['utc_now']())))
            response = session(con, uid, {'username':login, 'recoveryCode':code})
        return response

    @app.post('/password/login')
    def login(request: Request, payload: dict):
        name = username(payload.get('username'))
        guard(request, 'login', name)
        value = payload.get('password')
        if not isinstance(value,str) or not 1 <= len(value) <= 128 or len(value.encode('utf-8')) > 512:
            raise HTTPException(401, 'invalid_credentials')
        with db() as con:
            row = con.execute('SELECT p.user_id,p.salt,p.digest FROM account_passwords p JOIN users u ON u.id=p.user_id WHERE p.username=?', (name,)).fetchone()
        candidate = derive(value, row[1] if row else b'TOLF-dummy-salt!')
        if not row or not hmac.compare_digest(candidate, row[2]):
            raise HTTPException(401, 'invalid_credentials')
        with db() as con:
            con.execute('BEGIN IMMEDIATE')
            # A reset or account deletion during the KDF must invalidate this login.
            current = con.execute('SELECT p.digest FROM account_passwords p JOIN users u ON u.id=p.user_id WHERE p.user_id=?', (row[0],)).fetchone()
            if not current or not hmac.compare_digest(current[0], row[2]):
                raise HTTPException(401, 'invalid_credentials')
            response = session(con, row[0], {'username':name})
        return response

    @app.post('/password/recover')
    def recover(request: Request, payload: dict):
        name = username(payload.get('username'))
        guard(request, 'recover', name)
        code = payload.get('recoveryCode')
        if not isinstance(code,str) or not 1 <= len(code) <= 128:
            raise HTTPException(401, 'invalid_recovery')
        old_hash = ns['recovery_code_hash'](code)
        with db() as con:
            row = con.execute('SELECT u.id,u.recovery_code_hash FROM users u JOIN account_passwords p ON p.user_id=u.id WHERE p.username=?', (name,)).fetchone()
        if not row or not hmac.compare_digest(row[1], old_hash):
            raise HTTPException(401, 'invalid_recovery')
        value = password(payload.get('password'))
        salt = secrets.token_bytes(16)
        digest = derive(value, salt)
        new_code = ns['generate_recovery_code']()
        with db() as con:
            con.execute('BEGIN IMMEDIATE')
            # Code consumption, password replacement, session revocation are atomic.
            changed = con.execute('UPDATE users SET recovery_code_hash=? WHERE id=? AND recovery_code_hash=?',
                                  (ns['recovery_code_hash'](new_code),row[0],old_hash))
            if changed.rowcount != 1:
                raise HTTPException(401, 'invalid_recovery')
            con.execute('UPDATE account_passwords SET salt=?,digest=? WHERE user_id=?', (salt,digest,row[0]))
            con.execute('DELETE FROM sessions WHERE user_id=?', (row[0],))
            con.execute('DELETE FROM challenges WHERE user_id=?', (row[0],))
            response = session(con, row[0], {'username':name,'recoveryCode':new_code})
        return response
