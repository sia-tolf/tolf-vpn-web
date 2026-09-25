"""Admin inventory. VPN node state is never inferred from the account database."""
import json
import re
import secrets
import time
import sqlite3
import uuid
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
import tolf_nodes
from tolf_admin_session_parser import parse_inventory
from contextlib import contextmanager
from datetime import datetime, timezone

VERSION = '1.3.0'
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
        con.execute('CREATE TABLE IF NOT EXISTS admin_disconnect_tickets (ticket TEXT PRIMARY KEY,actor TEXT NOT NULL,node TEXT NOT NULL,selection TEXT NOT NULL,expires REAL NOT NULL,state TEXT NOT NULL,result TEXT,created REAL NOT NULL)')


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
        if node == 'moscow':
            command = ['/usr/bin/ssh', '-T', '-o', 'BatchMode=yes',
                       '-o', 'IdentitiesOnly=yes', '-o', 'ConnectTimeout=10',
                       '-o', 'StrictHostKeyChecking=yes',
                       '-o', 'UserKnownHostsFile=/etc/tolf-api/ssh/known_hosts',
                       '-i', '/etc/tolf-api/ssh/install_ru_sync_key',
                       'root@' + tolf_nodes.MOSCOW_PUBLIC_HOST,
                       'swanctl --list-sas --raw']
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=40, check=False)
            if result.returncode or len(result.stdout) > 8 * 1024 * 1024:
                return failed
            value = {'status': 'ok', 'version': '1.0.0', 'node': node,
                     'observedAt': datetime.now(timezone.utc).isoformat(),
                     'sessions': parse_inventory(result.stdout)}
        else:
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


TEST_ACCOUNT = '0888048c-ac6e-44d2-8aed-9857aa31e9ed'
TEST_USERNAME = 'user_0888048cac6e44d28aed9857aa31e9ed'
CONTROL_LOCK = threading.BoundedSemaphore(1)


def control_actor(request):
    actor = require_admin(request)
    # Browser calls must originate from our portal, with an explicit JSON request.
    if request.headers.get('origin') != 'https://vpn.tolf.is' or request.headers.get('content-type', '').split(';')[0].strip() != 'application/json':
        raise HTTPException(403, 'invalid_origin')
    with db() as con:
        row = con.execute('SELECT account_id,vpn_username FROM managed_users WHERE number=26 AND deleted_at IS NULL').fetchone()
        if not row or tuple(row) != (TEST_ACCOUNT, TEST_USERNAME) or actor == TEST_ACCOUNT:
            raise HTTPException(403, 'test_control_unavailable')
        if con.execute('SELECT 1 FROM vpn_imports WHERE user_id=? AND protected=1', (TEST_ACCOUNT,)).fetchone():
            raise HTTPException(403, 'test_control_unavailable')
    return actor


def control_call(node, selection=None):
    if node not in ('riga', 'moscow'):
        raise ValueError('invalid_node')
    remote = 'admin-test-sessions ' + node
    if selection is not None:
        validate_selection(selection)
        remote = 'admin-test-disconnect ' + node + ' ' + ' '.join(selection[k] for k in ('uniqueid', 'initiator-spi', 'responder-spi'))
    command = ['/usr/bin/ssh', '-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
               '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=yes',
               '-o', 'UserKnownHostsFile='+str(CTX['RIGA_KNOWN_HOSTS']),
               '-i', str(CTX['RIGA_KEY']), str(CTX['RIGA_USER'])+'@'+str(CTX['RIGA_HOST']), remote]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=40, check=False)
        if len(result.stdout) > 1024 * 1024:
            return {'status': 'unknown'}
        value = json.loads(result.stdout)
        if not isinstance(value, dict):
            return {'status': 'unknown'}
        if value.get('error') == 'stale_or_forbidden_session':
            return {'status': 'stale'}
        if result.returncode or value.get('status') != 'ok' or value.get('node') != node or value.get('accountNumber') != 26:
            return {'status': 'unknown'}
        if selection is None:
            sessions = value.get('sessions')
            if not isinstance(sessions, list) or len(sessions) > 1000:
                return {'status': 'unknown'}
            for item in sessions:
                validate_selection(item)
            if len({s['uniqueid'] for s in sessions}) != len(sessions):
                return {'status': 'unknown'}
            return {'status': 'ok', 'sessions': sessions}
        if value.get('disconnected') != selection['uniqueid'] or type(value.get('reconnected')) is not bool:
            return {'status': 'unknown'}
        return {'status': 'ok', 'reconnected': value['reconnected']}
    except (ValueError, TypeError, KeyError, OSError, subprocess.TimeoutExpired):
        return {'status': 'unknown'}


def validate_selection(item):
    if not isinstance(item, dict) or set(item) != {'uniqueid', 'initiator-spi', 'responder-spi'}:
        raise ValueError('invalid_selection')
    if any(not isinstance(v, str) for v in item.values()):
        raise ValueError('invalid_selection')
    if not re.fullmatch(r'[1-9][0-9]{0,9}', item['uniqueid']) or int(item['uniqueid']) > 4294967295:
        raise ValueError('invalid_selection')
    if any(not re.fullmatch(r'[0-9a-f]{16}', item[k]) for k in ('initiator-spi', 'responder-spi')):
        raise ValueError('invalid_selection')


def control_audit(con, actor, action, node, sid):
    target = 'Test #26 / ' + node + ((' / IKE #' + sid) if sid != '—' else '')
    con.execute('INSERT INTO admin_audit(actor,action,target,created_at) VALUES (?,?,?,?)',
                (actor, action, target, datetime.now(timezone.utc).isoformat()))


def access_call(action, revision=None):
    if action not in ('status', 'suspend', 'resume') or (action != 'status' and (not isinstance(revision, str) or not re.fullmatch('[0-9a-f]{32}', revision))):
        raise ValueError('invalid_access_command')
    remote = 'admin-test-access ' + action + ((' '+revision) if action != 'status' else '')
    command = ['/usr/bin/ssh', '-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
               '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=yes',
               '-o', 'UserKnownHostsFile='+str(CTX['RIGA_KNOWN_HOSTS']),
               '-i', str(CTX['RIGA_KEY']), str(CTX['RIGA_USER'])+'@'+str(CTX['RIGA_HOST']), remote]
    try:
        r = subprocess.run(command, capture_output=True, text=True, timeout=180 if action != 'status' else 40, check=False)
        if len(r.stdout) > 8192:
            return {'status': 'unknown'}
        result = json.loads(r.stdout)
        if not isinstance(result, dict):
            return {'status': 'unknown'}
        if result.get('error') == 'stale_revision':
            return {'status': 'stale'}
        if r.returncode or result.get('status') != 'ok' or result.get('accountNumber') != 26:
            return {'status': 'unknown'}
        state, rev = result.get('state'), result.get('revision')
        if state not in ('active', 'suspended', 'suspending', 'resuming') or not isinstance(rev, str) or not re.fullmatch('[0-9a-f]{32}', rev):
            return {'status': 'unknown'}
        return {'status': 'ok', 'state': state, 'revision': rev, 'accountNumber': 26}
    except (ValueError, TypeError, OSError, subprocess.TimeoutExpired):
        return {'status': 'unknown'}


def install(app, context):
    global CTX, HTTPException, JSONResponse
    from fastapi import HTTPException, Request
    from fastapi.responses import JSONResponse
    CTX = context
    initialize(CTX['DB'])

    @app.get('/admin/capabilities')
    def capabilities():
        return response({'version': VERSION, 'inventory': True, 'sessions': True, 'disconnect': False, 'testDisconnect': True, 'testAccess': True, 'suspend': False})

    @app.get('/admin/me')
    def me(request: Request):
        user_id = identity(request)
        with db() as con:
            number = con.execute('SELECT MIN(number) FROM managed_users WHERE account_id=? AND deleted_at IS NULL', (user_id,)).fetchone()[0]
            allowed = bool(con.execute('SELECT 1 FROM admin_roles WHERE user_id=?', (user_id,)).fetchone())
        return response({'isAdmin': allowed, 'number': number, 'features': {'sessions': True, 'testDisconnect': True, 'testAccess': True}})

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

    @app.post('/admin/disconnect/prepare')
    def prepare_disconnect(request: Request, body: dict):
        actor = control_actor(request)
        node, sid = body.get('node'), body.get('id')
        if set(body) != {'node', 'id'} or node not in ('riga', 'moscow') or type(sid) is not int or not 0 < sid <= 4294967295:
            raise HTTPException(400, 'invalid_selection')
        if not CONTROL_LOCK.acquire(blocking=False):
            raise HTTPException(429, 'control_busy')
        try:
            result = control_call(node)
            control_actor(request)  # role may have been revoked while SSH was running
            if result['status'] != 'ok':
                raise HTTPException(502, 'node_unavailable')
            matches = [s for s in result['sessions'] if s['uniqueid'] == str(sid)]
            if len(matches) != 1:
                raise HTTPException(409, 'stale_or_forbidden_session')
            ticket = secrets.token_urlsafe(32)
            now = time.time()
            with db() as con:
                con.execute("DELETE FROM admin_disconnect_tickets WHERE state='pending' AND expires<?", (now,))
                con.execute('INSERT INTO admin_disconnect_tickets VALUES (?,?,?,?,?,?,?,?)',
                            (ticket, actor, node, json.dumps(matches[0]), now+120, 'pending', None, now))
            return response({'ticket': ticket, 'accountNumber': 26, 'node': node, 'id': sid})
        finally:
            CONTROL_LOCK.release()

    @app.post('/admin/disconnect')
    def disconnect(request: Request, body: dict):
        actor = control_actor(request)
        ticket = body.get('ticket')
        if set(body) != {'ticket'} or not isinstance(ticket, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', ticket):
            raise HTTPException(400, 'invalid_ticket')
        if not CONTROL_LOCK.acquire(blocking=False):
            raise HTTPException(429, 'control_busy')
        try:
            with db() as con:
                con.execute('BEGIN IMMEDIATE')
                row = con.execute('SELECT * FROM admin_disconnect_tickets WHERE ticket=? AND actor=?', (ticket, actor)).fetchone()
                if not row:
                    raise HTTPException(409, 'invalid_ticket')
                if row['state'] != 'pending':
                    return response(json.loads(row['result']) if row['result'] else {'status': 'unknown'})
                if row['expires'] < time.time():
                    raise HTTPException(409, 'expired_ticket')
                selection = json.loads(row['selection'])
                validate_selection(selection)
                con.execute("UPDATE admin_disconnect_tickets SET state='attempted' WHERE ticket=?", (ticket,))
                control_audit(con, actor, 'session.disconnect.requested', row['node'], selection['uniqueid'])
            # A consumed ticket is NEVER resent, even after timeout or process restart.
            control_actor(request)
            result = control_call(row['node'], selection)
            with db() as con:
                con.execute("UPDATE admin_disconnect_tickets SET state='finished',result=? WHERE ticket=?", (json.dumps(result), ticket))
                control_audit(con, actor, 'session.disconnect.' + result['status'], row['node'], selection['uniqueid'])
            require_admin(request)
            return response(result)
        finally:
            CONTROL_LOCK.release()

    @app.get('/admin/test-access')
    def test_access_status(request: Request):
        require_admin(request)
        if not CONTROL_LOCK.acquire(blocking=False):
            raise HTTPException(429, 'control_busy')
        try:
            result = access_call('status')
            require_admin(request)
            return response(result)
        finally:
            CONTROL_LOCK.release()

    @app.post('/admin/test-access')
    def test_access_change(request: Request, body: dict):
        actor = control_actor(request)  # exact #26 mapping, no protected or own account
        action, revision = body.get('action'), body.get('revision')
        if set(body) != {'action', 'revision'} or action not in ('suspend', 'resume') or not isinstance(revision, str) or not re.fullmatch('[0-9a-f]{32}', revision):
            raise HTTPException(400, 'invalid_access_command')
        if not CONTROL_LOCK.acquire(blocking=False):
            raise HTTPException(429, 'control_busy')
        try:
            with db() as con:
                control_audit(con, actor, 'access.'+action+'.requested', 'riga+moscow', '—')
            control_actor(request)
            result = access_call(action, revision)
            with db() as con:
                control_audit(con, actor, 'access.'+action+'.'+result['status'], 'riga+moscow', '—')
            require_admin(request)
            return response(result)
        finally:
            CONTROL_LOCK.release()

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
