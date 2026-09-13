"""Authenticated, retryable adoption of a root-issued Riga invitation."""
import hashlib
import json
import re
import sqlite3
import subprocess
import time
import uuid
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

CTX = {}
TOKEN = re.compile(r'[A-Za-z0-9_-]{43}')
TERMINAL = {'invalid_invitation','invitation_used','invitation_expired','already_linked',
            'account_has_vpn','user_not_found','unsupported_credential_file','admin_invitation_required'}


def connect():
    return sqlite3.connect(CTX['DB'], timeout=30)


def require_ready(user_id):
    with connect() as con:
        row = con.execute('SELECT state FROM vpn_imports WHERE user_id=?', (user_id,)).fetchone()
    if row and row[0] != 'ready':
        raise HTTPException(409, 'Finish linking your existing VPN using the invitation first')


def before_account_delete(user_id):
    require_ready(user_id)
    with connect() as con:
        row = con.execute('SELECT protected FROM vpn_imports WHERE user_id=?', (user_id,)).fetchone()
    if row and row[0]:
        raise HTTPException(409, 'This VPN user is protected from deletion; contact the administrator')


def remote_claim(user_id, token):
    command = ['/usr/bin/ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',
               '-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+CTX['RIGA_KNOWN_HOSTS'],
               '-i',CTX['RIGA_KEY'],CTX['RIGA_USER']+'@'+CTX['RIGA_HOST'],
               'claim-existing '+str(uuid.UUID(user_id))+' '+token]
    try:
        result = subprocess.run(command,capture_output=True,text=True,timeout=120,check=False)
        value = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        raise HTTPException(502, 'Linking could not be confirmed. Retry the same invitation') from exc
    if not isinstance(value, dict):
        raise HTTPException(502, 'Invalid linking response')
    if result.returncode or value.get('status') != 'ok':
        code = value.get('code')
        if code in TERMINAL:
            raise HTTPException(409, code)
        raise HTTPException(502, 'Linking could not be confirmed. Retry the same invitation')
    if not re.fullmatch(r'[A-Za-z0-9_.@-]{1,128}', value.get('username','')) or type(value.get('protected')) is not bool:
        raise HTTPException(502, 'Invalid linking response')
    return value


def verification_limit(request):
    # Use ASGI's client address, not untrusted forwarded headers supplied by a caller.
    address = request.client.host if request.client else 'unknown'
    keys = [('global',200), (hashlib.sha256(address.encode()).hexdigest(),10)]
    now = time.time()
    with connect() as con:
        con.execute('BEGIN IMMEDIATE')
        con.execute('DELETE FROM vpn_verify_attempts WHERE started<?', (now-900,))
        for key,maximum in keys:
            row = con.execute('SELECT count FROM vpn_verify_attempts WHERE key=?', (key,)).fetchone()
            if row and row[0]>=maximum:
                raise HTTPException(429,'too_many_attempts',headers={'Retry-After':'900'})
        for key,_ in keys:
            con.execute('INSERT INTO vpn_verify_attempts VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET count=count+1', (key,now))


def verify(request: Request, payload: dict):
    if request.headers.get('origin') != CTX['ORIGIN']:
        raise HTTPException(403,'Invalid origin')
    verification_limit(request)
    username, password = payload.get('username'), payload.get('password')
    if not isinstance(username,str) or not re.fullmatch(r'[A-Za-z0-9_.@-]{1,128}',username) or not isinstance(password,str) or not 1<=len(password)<=256:
        raise HTTPException(400,'invalid_credentials')
    if username in {'user0','user0_ipad'}:
        raise HTTPException(403,'admin_invitation_required')
    remote_payload = {'username':username,'password':password}
    try:
        retry_id = CTX['authenticated_user_id'](request)
    except HTTPException as exc:
        if exc.status_code != 401: raise
    else:
        with connect() as con:
            pending = con.execute("SELECT 1 FROM vpn_imports WHERE user_id=? AND state='pending'", (retry_id,)).fetchone()
        if pending: remote_payload['retryAccount'] = retry_id
    command = ['/usr/bin/ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',
               '-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+CTX['RIGA_KNOWN_HOSTS'],
               '-i',CTX['RIGA_KEY'],CTX['RIGA_USER']+'@'+CTX['RIGA_HOST'],'verify-existing']
    try:
        result = subprocess.run(command, input=json.dumps(remote_payload),
                                capture_output=True,text=True,timeout=30,check=False)
        value = json.loads(result.stdout)
    except (subprocess.TimeoutExpired,json.JSONDecodeError,OSError) as exc:
        raise HTTPException(502,'verification_unavailable') from exc
    if not isinstance(value,dict): raise HTTPException(502,'verification_unavailable')
    if result.returncode or value.get('status')!='ok':
        code = value.get('code')
        if code=='too_many_attempts': raise HTTPException(429,code,headers={'Retry-After':'900'})
        if code in {'invalid_credentials','admin_invitation_required','already_linked'}:
            raise HTTPException(403,code)
        raise HTTPException(502,'verification_unavailable')
    if not isinstance(value.get('token'),str) or not TOKEN.fullmatch(value['token']) or value.get('username')!=username:
        raise HTTPException(502,'verification_unavailable')
    return JSONResponse({'status':'ok','token':value['token'],'username':username,'expiresIn':900}, headers={'Cache-Control':'no-store'})


def claim(request: Request, payload: dict):
    if request.headers.get('origin') != CTX['ORIGIN']:
        raise HTTPException(403, 'Invalid origin')
    user_id = CTX['authenticated_user_id'](request)
    token = payload.get('token')
    if not isinstance(token,str) or not TOKEN.fullmatch(token):
        raise HTTPException(400, 'invalid_invitation')
    digest = hashlib.sha256(token.encode()).hexdigest()
    with CTX['tolf_promos'].account_operation(CTX['DB'],user_id):
        with connect() as con:
            previous = con.execute('SELECT digest,state,username FROM vpn_imports WHERE user_id=?',(user_id,)).fetchone()
            if previous:
                if previous[0] != digest and previous[1]=='ready':
                    raise HTTPException(409, 'account_has_vpn')
                if previous[1] == 'ready':
                    if not CTX['vpn_record'](user_id):
                        raise HTTPException(409, 'invitation_used')
                    return {'status':'ok','username':previous[2]}
            elif CTX['vpn_record'](user_id):
                raise HTTPException(409,'account_has_vpn')
            else:
                con.execute('INSERT INTO vpn_imports(user_id,digest,state) VALUES(?,?,?)', (user_id,digest,'pending'))
        try:
            value = remote_claim(user_id,token)
        except HTTPException as exc:
            if exc.detail in TERMINAL and (not previous or previous[0]==digest):
                with connect() as con:
                    con.execute("DELETE FROM vpn_imports WHERE user_id=? AND state='pending'", (user_id,))
            raise
        with connect() as con:
            con.execute('INSERT INTO vpn_access(user_id,vpn_username,created_at,server) VALUES(?,?,?,?)',
                        (user_id,value['username'],CTX['utc_iso'](CTX['utc_now']()),'riga'))
            con.execute("UPDATE vpn_imports SET state='ready',username=?,protected=?,digest=? WHERE user_id=?",
                        (value['username'],int(value['protected']),digest,user_id))
    return {'status':'ok','username':value['username']}


def status(request: Request):
    user_id = CTX['authenticated_user_id'](request)
    with connect() as con:
        row = con.execute('SELECT state,protected FROM vpn_imports WHERE user_id=?', (user_id,)).fetchone()
    return {'imported':bool(row), 'pending':bool(row and row[0]!='ready'), 'protected':bool(row and row[1])}


def install(app, context):
    CTX.update(context)
    with connect() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS vpn_imports (
            user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            digest TEXT NOT NULL, state TEXT NOT NULL,
            username TEXT UNIQUE, protected INTEGER NOT NULL DEFAULT 0)''')
    with connect() as con:
        con.execute('CREATE TABLE IF NOT EXISTS vpn_verify_attempts (key TEXT PRIMARY KEY, started REAL, count INTEGER)')
    app.post('/vpn/invitations/verify')(verify)
    app.post('/vpn/invitations/claim')(claim)
    app.get('/vpn/invitations/status')(status)
    app.get('/vpn/invitations/capabilities')(lambda: {'version': 2, 'passwordLinking': True})
