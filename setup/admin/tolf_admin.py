"""Admin inventory. VPN node state is never inferred from the account database."""
import json
import sqlite3
import uuid
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone

VERSION = '1.1.0'
SESSION_POLL = threading.BoundedSemaphore(1)
HEADERS = {'Cache-Control': 'private, no-store, max-age=0', 'X-Content-Type-Options': 'nosniff'}
CTX = {}

@contextmanager
def db():
    con = sqlite3.connect(CTX['DB'], timeout=15)
    con.row_factory = sqlite3.Row
    try:
        with con:
            yield con
    finally:
        con.close()


def initialize(path):
    with sqlite3.connect(path, timeout=15) as con:
        con.execute('CREATE TABLE IF NOT EXISTS admin_roles (user_id TEXT PRIMARY KEY, granted_at TEXT NOT NULL, granted_by TEXT NOT NULL)')
        con.execute('CREATE TABLE IF NOT EXISTS admin_audit (id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT NOT NULL, action TEXT NOT NULL, target TEXT NOT NULL, created_at TEXT NOT NULL)')


def root_grant(path, number):
    # Called only by the root-only installation utility, never by an HTTP route.
    initialize(path)
    with sqlite3.connect(path, timeout=15) as con:
        con.execute('BEGIN IMMEDIATE')
        rows = con.execute('SELECT DISTINCT u.id FROM managed_users m JOIN users u ON u.id=m.account_id WHERE m.number=? AND m.deleted_at IS NULL', (number,)).fetchall()
        if len(rows) != 1:
            raise ValueError('Number must identify exactly one existing account')
        user_id = rows[0][0]
        stamp = datetime.now(timezone.utc).isoformat()
        if not con.execute('SELECT 1 FROM admin_roles WHERE user_id=?', (user_id,)).fetchone():
            con.execute('INSERT INTO admin_roles VALUES (?,?,?)', (user_id,stamp,'root'))
            con.execute('INSERT INTO admin_audit(actor,action,target,created_at) VALUES (?,?,?,?)', ('root','admin.grant',user_id,stamp))
        return user_id


def root_revoke(path, number):
    initialize(path)
    with sqlite3.connect(path, timeout=15) as con:
        con.execute('BEGIN IMMEDIATE')
        rows = con.execute('SELECT DISTINCT account_id FROM managed_users WHERE number=?', (number,)).fetchall()
        if len(rows) != 1 or not rows[0][0]:
            raise ValueError('Number must identify exactly one account')
        user_id = rows[0][0]
        if con.execute('DELETE FROM admin_roles WHERE user_id=?', (user_id,)).rowcount:
            con.execute('INSERT INTO admin_audit(actor,action,target,created_at) VALUES (?,?,?,?)', ('root','admin.revoke',user_id,datetime.now(timezone.utc).isoformat()))
        return user_id


def identity(request):
    user_id = CTX['authenticated_user_id'](request)
    with db() as con:
        if not con.execute('SELECT 1 FROM users WHERE id=?', (user_id,)).fetchone():
            raise HTTPException(401, 'authentication_required')
    return user_id


def require_admin(request):
    user_id = identity(request)
    with db() as con:
        if not con.execute('SELECT 1 FROM admin_roles WHERE user_id=?', (user_id,)).fetchone():
            raise HTTPException(403, 'administrator_required')
    return user_id


def response(data):
    return JSONResponse(data, headers=HEADERS)


def user_record(con, row):
    user_id = row['id']
    number = con.execute('SELECT MIN(number) FROM managed_users WHERE account_id=? AND deleted_at IS NULL', (user_id,)).fetchone()[0]
    access = [dict(r) for r in con.execute('SELECT vpn_username AS username, server, created_at AS createdAt FROM vpn_access WHERE user_id=?', (user_id,))]
    return {'id': user_id, 'number': number, 'createdAt': row['created_at'], 'access': access,
            'passkeys': con.execute('SELECT count(*) FROM passkeys WHERE user_id=?', (user_id,)).fetchone()[0],
            'windowsDevices': con.execute("SELECT count(*) FROM windows_devices WHERE user_id=? AND state!='deleted'", (user_id,)).fetchone()[0],
            'isAdmin': bool(con.execute('SELECT 1 FROM admin_roles WHERE user_id=?', (user_id,)).fetchone()),
            'protected': bool(con.execute('SELECT 1 FROM vpn_imports WHERE user_id=? AND protected=1', (user_id,)).fetchone())}


def query_node(node):
    # Node names are fixed by the caller; no browser input enters SSH commands.
    if node not in ('riga', 'moscow'):
        raise ValueError('invalid node')
    stamp = datetime.now(timezone.utc).isoformat()
    failed = {'node': node, 'status': 'error', 'attemptedAt': stamp, 'error': 'node_unavailable'}
    try:
        command = ['/usr/bin/ssh', '-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
                   '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=yes',
                   '-o', 'UserKnownHostsFile='+str(CTX['RIGA_KNOWN_HOSTS']),
                   '-i', str(CTX['RIGA_KEY']), str(CTX['RIGA_USER'])+'@'+str(CTX['RIGA_HOST']),
                   'admin-sessions '+node]
        result = subprocess.run(command, capture_output=True, text=True, timeout=40, check=False)
        if result.returncode or len(result.stdout) > 8 * 1024 * 1024:
            return failed
        value = json.loads(result.stdout)
        if not isinstance(value, dict) or value.get('status') != 'ok' or value.get('node') != node or value.get('version') != '1.0.0':
            return failed
        observed = value.get('observedAt')
        parsed = datetime.fromisoformat(observed)
        if parsed.utcoffset() is None:
            return failed
        source = value.get('sessions')
        if not isinstance(source, list) or len(source) > 10000:
            return failed
        sessions = []
        ids = set()
        for row in source:
            if not isinstance(row, dict):
                return failed
            clean = {}
            for key in ('id', 'establishedSeconds', 'bytesIn', 'bytesOut'):
                v = row.get(key)
                if key == 'establishedSeconds' and v is None:
                    clean[key] = None
                    continue
                if type(v) is not int or v < 0:
                    return failed
                clean[key] = v
            if clean['id'] in ids:
                return failed
            ids.add(clean['id'])
            for key in ('connection', 'state', 'identity', 'identitySource', 'remoteHost'):
                v = row.get(key)
                if v is not None and (not isinstance(v, str) or len(v) > 1024):
                    return failed
                clean[key] = v
            if clean['identitySource'] not in ('remote-id', 'remote-eap-id'):
                return failed
            vips = row.get('virtualAddresses')
            if not isinstance(vips, list) or len(vips) > 32 or any(not isinstance(v, str) or len(v) > 128 for v in vips):
                return failed
            clean['virtualAddresses'] = vips
            sessions.append(clean)
        return {'node': node, 'status': 'ok', 'observedAt': observed, 'sessions': sessions}
    except (KeyError, ValueError, TypeError, OSError, subprocess.TimeoutExpired):
        return failed


def map_session(con, session):
    username = session.get('identity')
    if not username:
        return None
    rows = con.execute("SELECT account_id,number FROM managed_users WHERE vpn_username=? AND deleted_at IS NULL", (username,)).fetchall()
    rows += con.execute("SELECT w.user_id,m.number FROM windows_devices w JOIN users u ON u.id=w.user_id LEFT JOIN managed_users m ON m.account_id=w.user_id AND m.deleted_at IS NULL WHERE w.username=? AND w.state!='deleted'", (username,)).fetchall()
    matches = {(row[0], row[1]) for row in rows}
    # Display-only registry match; never authorization for a mutation.
    if len(matches) != 1:
        return None
    account_id, number = matches.pop()
    return {'accountId': account_id, 'number': number}


def install(app, context):
    global CTX, HTTPException, JSONResponse
    from fastapi import HTTPException, Request
    from fastapi.responses import JSONResponse
    CTX = context
    initialize(CTX['DB'])

    @app.get('/admin/capabilities')
    def capabilities():
        return response({'version': VERSION, 'inventory': True, 'sessions': True, 'disconnect': False, 'suspend': False})

    @app.get('/admin/me')
    def me(request: Request):
        user_id = identity(request)
        with db() as con:
            number = con.execute('SELECT MIN(number) FROM managed_users WHERE account_id=? AND deleted_at IS NULL', (user_id,)).fetchone()[0]
            allowed = bool(con.execute('SELECT 1 FROM admin_roles WHERE user_id=?', (user_id,)).fetchone())
        return response({'isAdmin': allowed, 'number': number, 'features': {'sessions': True}})

    @app.get('/admin/sessions')
    def sessions(request: Request):
        require_admin(request)
        if not SESSION_POLL.acquire(blocking=False):
            raise HTTPException(429, 'session_poll_in_progress')
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(query_node, ('riga', 'moscow')))
            # Recheck after the remote wait, so a revoked role cannot receive a late response.
            require_admin(request)
            with db() as con:
                for result in results:
                    if result['status'] == 'ok':
                        for session in result['sessions']:
                            session['account'] = map_session(con, session)
            return response({'nodes': results, 'source': 'vpn_nodes'})
        finally:
            SESSION_POLL.release()

    @app.get('/admin/users')
    def users(request: Request, q: str = '', offset: int = 0, limit: int = 50):
        require_admin(request)
        if offset < 0 or not 1 <= limit <= 100 or len(q) > 128:
            raise HTTPException(400, 'invalid_query')
        q = q.strip()
        # instr searches literally: %, _ and SQL-looking input have no special meaning.
        where = '''WHERE (?='' OR instr(lower(u.id),lower(?))>0
            OR EXISTS(SELECT 1 FROM managed_users m WHERE m.account_id=u.id AND (CAST(m.number AS TEXT)=? OR instr(lower(COALESCE(m.vpn_username,'')),lower(?))>0))
            OR EXISTS(SELECT 1 FROM windows_devices w WHERE w.user_id=u.id AND w.state!='deleted' AND instr(lower(w.name),lower(?))>0))'''
        args = (q,q,q,q,q)
        with db() as con:
            total = con.execute('SELECT count(*) FROM users u '+where,args).fetchone()[0]
            rows = con.execute('SELECT u.id,u.created_at FROM users u '+where+' ORDER BY u.created_at DESC,u.id LIMIT ? OFFSET ?', args+(limit,offset)).fetchall()
            values = [user_record(con,r) for r in rows]
        return response({'users':values,'total':total,'offset':offset,'limit':limit,'observedAt':datetime.now(timezone.utc).isoformat(),'source':'account_database'})

    @app.get('/admin/users/{user_id}')
    def details(user_id: str, request: Request):
        require_admin(request)
        try:
            user_id = str(uuid.UUID(user_id))
        except ValueError:
            raise HTTPException(400, 'invalid_user_id')
        with db() as con:
            row = con.execute('SELECT id,created_at FROM users WHERE id=?', (user_id,)).fetchone()
            if not row:
                raise HTTPException(404, 'user_not_found')
            result = user_record(con,row)
            result['devices'] = [dict(r) for r in con.execute("SELECT w.id,w.name,w.username,w.state,w.created_at AS createdAt,COALESCE(n.server,'riga') AS server FROM windows_devices w LEFT JOIN windows_device_nodes n ON n.device_id=w.id WHERE w.user_id=? AND w.state!='deleted' ORDER BY w.created_at,w.id",(user_id,))]
            result['passkeyNames'] = [r[0] or '' for r in con.execute('SELECT name FROM passkeys WHERE user_id=? ORDER BY created_at',(user_id,))]
        return response(result)

    @app.get('/admin/registry')
    def registry(request: Request, offset: int = 0, limit: int = 50):
        require_admin(request)
        if offset < 0 or not 1 <= limit <= 100:
            raise HTTPException(400, 'invalid_query')
        with db() as con:
            total = con.execute('SELECT count(*) FROM managed_users WHERE deleted_at IS NULL').fetchone()[0]
            rows = con.execute('SELECT number,account_id AS accountId,vpn_username AS username,created_at AS createdAt,source,vpn_active AS provisioned FROM managed_users WHERE deleted_at IS NULL ORDER BY number LIMIT ? OFFSET ?', (limit,offset)).fetchall()
        return response({'records':[dict(r) for r in rows],'total':total,'offset':offset,'limit':limit,'source':'account_database'})

    @app.get('/admin/audit')
    def audit(request: Request):
        require_admin(request)
        with db() as con:
            rows = con.execute('SELECT actor,action,target,created_at AS createdAt FROM admin_audit ORDER BY id DESC LIMIT 100').fetchall()
        return response({'events':[dict(r) for r in rows]})
