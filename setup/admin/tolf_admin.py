"""Admin inventory. VPN node state is never inferred from the account database."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

VERSION = '1.0.0'
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


def install(app, context):
    global CTX, HTTPException, JSONResponse
    from fastapi import HTTPException, Request
    from fastapi.responses import JSONResponse
    CTX = context
    initialize(CTX['DB'])

    @app.get('/admin/capabilities')
    def capabilities():
        return response({'version': VERSION, 'inventory': True, 'sessions': False, 'disconnect': False, 'suspend': False})

    @app.get('/admin/me')
    def me(request: Request):
        user_id = identity(request)
        with db() as con:
            number = con.execute('SELECT MIN(number) FROM managed_users WHERE account_id=? AND deleted_at IS NULL', (user_id,)).fetchone()[0]
            allowed = bool(con.execute('SELECT 1 FROM admin_roles WHERE user_id=?', (user_id,)).fetchone())
        return response({'isAdmin': allowed, 'number': number})

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
