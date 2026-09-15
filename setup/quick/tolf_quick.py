"""Quick setup: authenticated, durable selection; delegates VPN work to existing APIs."""
import datetime
from contextlib import closing, contextmanager
import fcntl
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import uuid
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

VERSION = 1
HEADERS = {'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'}


def allowed_servers(db, user_id):
    # Geography chooses a recommendation, never authorization. Authentication remains
    # at the caller; the provisioning service still enforces administrative suspension.
    return ['riga', 'moscow']


def registration_session(result, ns):
    """Called only after the existing registration handler verified and committed a Passkey."""
    user_id = str(uuid.UUID(result['userId']))
    now = ns['utc_now']()
    token = secrets.token_urlsafe(32)
    expires = now + datetime.timedelta(days=ns['SESSION_DAYS'])
    with closing(sqlite3.connect(ns['DB'], timeout=30)) as con, con:
        if not con.execute('SELECT 1 FROM users WHERE id=?', (user_id,)).fetchone():
            raise HTTPException(409, 'Account not found')
        con.execute('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES (?,?,?,?)',
                    (hashlib.sha256(token.encode()).digest(), user_id, ns['utc_iso'](now), ns['utc_iso'](expires)))
    response = JSONResponse(result, headers=HEADERS)
    response.set_cookie(key=ns['SESSION_COOKIE'], value=token, max_age=ns['SESSION_DAYS']*86400,
                        httponly=True, secure=True, samesite='lax', path='/')
    return response


def install(app, ns):
    lock_dir = Path(ns['DB']).parent / 'quick-locks'
    lock_dir.mkdir(mode=0o700, exist_ok=True)
    with closing(sqlite3.connect(ns['DB'], timeout=30)) as con, con:
        con.execute('''CREATE TABLE IF NOT EXISTS quick_setups (
            user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            platform TEXT NOT NULL, server TEXT NOT NULL, request_id TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'pending')''')

    @contextmanager
    def connect():
        con = sqlite3.connect(ns['DB'], timeout=30)
        con.row_factory = sqlite3.Row
        try:
            with con:
                yield con
        finally:
            con.close()

    def origin(request):
        if request.headers.get('origin') != ns['ORIGIN']:
            raise HTTPException(403, 'Invalid origin')

    def public(row):
        return {key: row[key] for key in ('platform', 'server', 'state')} if row else None

    # Retrieve endpoint functions once; each still performs its own authentication,
    # ownership checks, account lock, node validation and credential provisioning.
    endpoints = {(r.path, method): r.endpoint for r in app.routes for method in (getattr(r, 'methods', None) or [])}
    windows_create = endpoints[('/windows/devices', 'POST')]

    @app.get('/quick-setup/capabilities')
    def capabilities():
        return JSONResponse({'version': VERSION, 'servers': ['riga', 'moscow']}, headers=HEADERS)

    @app.get('/quick-setup/status')
    def status(request: Request):
        user = ns['authenticated_user_id'](request)
        with connect() as con:
            row = con.execute('SELECT * FROM quick_setups WHERE user_id=?', (user,)).fetchone()
        return JSONResponse({'setup': public(row)}, headers=HEADERS)

    @app.post('/quick-setup/prepare')
    def prepare(request: Request, payload: dict):
        origin(request)
        user = str(uuid.UUID(ns['authenticated_user_id'](request)))
        platform, server = payload.get('platform'), payload.get('server')
        language = payload.get('language', 'en')
        if platform not in ('ios', 'android', 'windows') or server not in ('riga', 'moscow') or language not in ('ru', 'en', 'lv'):
            raise HTTPException(400, 'Invalid selection')
        # Distinct from the existing account lock to avoid recursive flock deadlocks.
        with open(lock_dir / user, 'a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise HTTPException(409, 'Setup is already running')
            with connect() as con:
                con.execute('INSERT OR IGNORE INTO quick_setups(user_id,platform,server,request_id) VALUES (?,?,?,?)',
                            (user, platform, server, str(uuid.uuid4())))
                row = con.execute('SELECT * FROM quick_setups WHERE user_id=?', (user,)).fetchone()
            if row['platform'] != platform or row['server'] != server:
                raise HTTPException(409, 'Continue the saved setup')
            selection = {'platform': platform, 'server': server, 'language': language,
                         'localId': 'sr' if server == 'riga' else '', 'dnsMode': 'tolf',
                         'dnsServers': [], 'onDemandEnabled': False, 'onDemandRules': []}
            if platform == 'windows':
                data = windows_create(request, {'requestId': row['request_id'], 'name': 'Windows',
                                                'server': server, 'language': language})
            else:
                if ns['vpn_record'](user):
                    data = ns['vpn_profile'](request, selection)
                else:
                    try:
                        data = ns['vpn_create'](request, selection)
                    except HTTPException as exc:
                        # Creation may have completed in another tab or after a lost reply.
                        if exc.status_code != 409 or not ns['vpn_record'](user):
                            raise
                        data = ns['vpn_profile'](request, selection)
            if not isinstance(data, dict) or not data.get('profileUrl'):
                raise HTTPException(502, 'Profile was not returned')
            with connect() as con:
                con.execute("UPDATE quick_setups SET state='ready' WHERE user_id=?", (user,))
            return JSONResponse({'profileUrl': data['profileUrl'], 'platform': platform, 'server': server}, headers=HEADERS)
