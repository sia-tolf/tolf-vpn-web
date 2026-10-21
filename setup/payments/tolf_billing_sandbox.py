"""Montonio SANDBOX only. Does not touch live traffic, quotas or money."""
import hashlib
import hmac
import json
import re
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request as UrlRequest, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

import jwt
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

CONFIG = Path('/etc/tolf-payments/montonio-sandbox.json')
DATABASE = Path('/var/lib/tolf-api/montonio-sandbox.db')
BASE = 'https://sandbox-stargate.montonio.com/api'
ORIGIN = 'https://vpn.tolf.is'
TERMS = '2026-10-21'
PACKAGES = {'50': (50,300), '200': (200,900), '500': (500,2000)}
METHODS = {'cardPayments','paymentInitiation','applePay','googlePay'}
HEADERS = {'Cache-Control':'no-store', 'Referrer-Policy':'no-referrer'}

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def config():
    try:
        data=json.loads(CONFIG.read_text())
        if data.get('environment')!='sandbox' or data.get('apiBase')!=BASE:
            raise ValueError()
        if not all(isinstance(data.get(k),str) and data[k] for k in ['accessKey','secretKey','storeUuid']):
            raise ValueError()
        return data
    except (OSError,ValueError,TypeError):
        raise HTTPException(503,'sandbox_not_configured')

def provider(method,path,payload=None):
    cfg=config()
    now=int(time.time())
    claims={'accessKey':cfg['accessKey'],'iat':now,'exp':now+120,**(payload or {})}
    token=jwt.encode(claims,cfg['secretKey'],algorithm='HS256')
    headers={'Accept':'application/json','Content-Type':'application/json'}
    body=None
    if method=='GET':
        headers['Authorization']='Bearer '+token
    else:
        body=json.dumps({'data':token}).encode()
    # No caller-supplied host, no redirects and no live fallback.
    if not re.fullmatch(r'/stores/payment-methods|/orders(?:/[a-fA-F0-9-]{36})?',path):
        raise RuntimeError('Invalid internal provider path')
    try:
        with build_opener(NoRedirect()).open(UrlRequest(BASE+path,data=body,headers=headers,method=method),timeout=18) as resp:
            raw=resp.read(2_000_001)
            if len(raw)>2_000_000:
                raise ValueError()
            data=json.loads(raw)
        if not isinstance(data,dict):
            raise ValueError()
        return data
    except HTTPError as exc:
        # Never expose provider request bodies/JWTs/keys to callers or logs.
        raise HTTPException(502,'sandbox_provider_http_'+str(exc.code))
    except (URLError,TimeoutError,OSError,ValueError):
        raise HTTPException(502,'sandbox_provider_unavailable')

@contextmanager
def database():
    con=sqlite3.connect(DATABASE,timeout=15)
    con.row_factory=sqlite3.Row
    try:
        with con:
            yield con
    finally:
        con.close()

def initialize():
    with database() as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
            reference TEXT PRIMARY KEY, user_id TEXT NOT NULL, request_id TEXT NOT NULL,
            sku TEXT NOT NULL, gb INTEGER NOT NULL, cents INTEGER NOT NULL,
            method TEXT NOT NULL, locale TEXT NOT NULL, status TEXT NOT NULL,
            provider_uuid TEXT UNIQUE, payment_url TEXT,
            terms_version TEXT NOT NULL, early_service INTEGER NOT NULL,
            created REAL NOT NULL, updated REAL NOT NULL,
            last_provider_check REAL NOT NULL DEFAULT 0,
            webhook_count INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id,request_id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS credits (
            order_reference TEXT PRIMARY KEY REFERENCES orders(reference),
            user_id TEXT NOT NULL, bytes INTEGER NOT NULL, created REAL NOT NULL)''')
        c.execute('CREATE INDEX IF NOT EXISTS orders_user ON orders(user_id,created)')
    DATABASE.chmod(0o600)

def money(value):
    try:
        number=Decimal(str(value))
        if not number.is_finite() or number<0 or number*100 != (number*100).to_integral_value():
            raise ValueError()
        return int(number*100)
    except (InvalidOperation,TypeError,ValueError):
        raise HTTPException(400,'invalid_payment_amount')

def matching_order(data,row):
    cfg=config()
    if not hmac.compare_digest(str(data.get('accessKey',cfg['accessKey'])),cfg['accessKey']):
        raise HTTPException(400,'wrong_merchant')
    if data.get('storeUuid',cfg['storeUuid']) != cfg['storeUuid']:
        raise HTTPException(400,'wrong_store')
    if data.get('merchantReference')!=row['reference'] or data.get('currency')!='EUR' or money(data.get('grandTotal'))!=row['cents']:
        raise HTTPException(400,'order_mismatch')
    try:
        provider_id=str(uuid.UUID(data.get('uuid','')))
    except (ValueError,TypeError,AttributeError):
        raise HTTPException(400,'invalid_provider_order')
    if row['provider_uuid'] and row['provider_uuid']!=provider_id:
        raise HTTPException(400,'order_uuid_mismatch')
    return provider_id

def apply_status(data,source):
    reference=data.get('merchantReference')
    with database() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM orders WHERE reference=?',(reference,)).fetchone()
        if not row:
            raise HTTPException(404,'unknown_sandbox_order')
        provider_id=matching_order(data,row)
        status=data.get('paymentStatus')
        if status not in {'PENDING','PAID','ABANDONED','VOIDED','DECLINED','CANCELLED','EXPIRED','AUTHORIZED'}:
            raise HTTPException(400,'unknown_payment_status')
        # Late pending/failed notifications cannot reverse a paid order.
        if row['status']=='PAID':
            status='PAID'
        if status=='PAID':
            c.execute('INSERT OR IGNORE INTO credits VALUES (?,?,?,?)',
                      (reference,row['user_id'],row['gb']*1_000_000_000,time.time()))
        c.execute('UPDATE orders SET provider_uuid=?,status=?,updated=?,webhook_count=webhook_count+? WHERE reference=?',
                  (provider_id,status,time.time(),1 if source=='webhook' else 0,reference))
    return reference

def decode_notification(token):
    cfg=config()
    if not isinstance(token,str) or len(token)>12000:
        raise HTTPException(400,'invalid_order_token')
    try:
        data=jwt.decode(token,cfg['secretKey'],algorithms=['HS256'],
                        options={'require':['exp','iat','accessKey','uuid','merchantReference','currency','grandTotal','paymentStatus']},
                        leeway=15)
    except jwt.InvalidTokenError:
        raise HTTPException(400,'invalid_order_token')
    if not hmac.compare_digest(str(data['accessKey']),cfg['accessKey']):
        raise HTTPException(400,'wrong_merchant')
    return data

def public_order(row):
    return {'reference':row['reference'],'package':row['sku'],'gb':row['gb'],
            'amount':row['cents']/100,'currency':'EUR','status':row['status'],
            'createdAt':row['created'],'updatedAt':row['updated'],
            'mode':'sandbox','paymentUrl':row['payment_url'] if row['status']=='PENDING' else None}

def install(app,ns):
    initialize()
    methods_lock=threading.Lock()
    cache={'until':0,'data':None}

    def allowed(request):
        uid=ns['authenticated_user_id'](request)
        cfg=config()
        with sqlite3.connect(ns['DB']) as c:
            admin=c.execute('SELECT 1 FROM admin_roles WHERE user_id=?',(uid,)).fetchone()
        if uid not in cfg.get('reviewerIds',[]) and not admin:
            raise HTTPException(403,'sandbox_review_only')
        return uid

    def enabled_methods():
        with methods_lock:
            if time.time()<cache['until']:
                return cache['data']
            data=provider('GET','/stores/payment-methods')
            if data.get('uuid')!=config()['storeUuid']:
                raise HTTPException(502,'sandbox_store_mismatch')
            raw=data.get('paymentMethods',{})
            result={'methods':[m for m in ['cardPayments','paymentInitiation','applePay','googlePay'] if m in raw],
                    'banks':{}}
            for country,setup in raw.get('paymentInitiation',{}).get('setup',{}).items():
                banks=[{'code':b['code'],'name':b['name']} for b in setup.get('paymentMethods',[]) if 'EUR' in b.get('supportedCurrencies',[])]
                if banks:
                    result['banks'][country]=banks
            cache.update(until=time.time()+300,data=result)
            return result

    async def read_payload(request,check_origin=True):
        if check_origin and request.headers.get('origin')!=ORIGIN:
            raise HTTPException(403,'invalid_origin')
        if request.headers.get('content-type','').split(';')[0].strip()!='application/json':
            raise HTTPException(415,'json_required')
        raw=b''
        async for chunk in request.stream():
            raw+=chunk
            if len(raw)>16000:
                raise HTTPException(413,'payload_too_large')
        try:
            data=json.loads(raw)
            if not isinstance(data,dict):
                raise ValueError()
            return data
        except (ValueError,TypeError):
            raise HTTPException(400,'invalid_json')

    @app.get('/billing/capabilities')
    def capabilities(request:Request):
        try:
            allowed(request)
        except HTTPException as exc:
            if exc.status_code in (401,403,503):
                return JSONResponse({'mode':'preview','enabled':False},headers=HEADERS)
            raise
        return JSONResponse({'mode':'sandbox','enabled':True,'termsVersion':TERMS,'livePayments':False},headers=HEADERS)

    @app.get('/billing/sandbox/methods')
    def methods(request:Request):
        allowed(request)
        return JSONResponse(enabled_methods(),headers=HEADERS)

    @app.get('/billing/sandbox/account')
    def account(request:Request):
        uid=allowed(request)
        with database() as c:
            rows=c.execute('SELECT * FROM orders WHERE user_id=? ORDER BY created DESC LIMIT 30',(uid,)).fetchall()
            balance=c.execute('SELECT COALESCE(SUM(bytes),0) FROM credits WHERE user_id=?',(uid,)).fetchone()[0]
        return JSONResponse({'mode':'sandbox','testBalanceBytes':balance,'orders':[public_order(x) for x in rows]},headers=HEADERS)

    def create(uid,p):
        expected={'package','method','locale','bankCountry','bankCode','requestId','termsVersion','acceptTerms','startNow'}
        if set(p)-expected:
            raise HTTPException(400,'unexpected_checkout_fields')
        sku=p.get('package')
        if not isinstance(sku,str) or sku not in PACKAGES:
            raise HTTPException(400,'invalid_package')
        if p.get('termsVersion')!=TERMS or p.get('acceptTerms') is not True or p.get('startNow') is not True:
            raise HTTPException(400,'checkout_consent_required')
        method=p.get('method')
        methods=enabled_methods()
        if method not in methods['methods']:
            raise HTTPException(400,'payment_method_unavailable')
        locale=p.get('locale')
        if not isinstance(locale,str) or locale not in {'en','ru','lv'}:
            raise HTTPException(400,'invalid_locale')
        options={}
        if method=='paymentInitiation':
            country=p.get('bankCountry')
            bank=p.get('bankCode')
            if not any(x['code']==bank for x in methods['banks'].get(country,[])):
                raise HTTPException(400,'invalid_bank')
            options={'preferredCountry':country,'preferredProvider':bank}
        try:
            request_id=str(uuid.UUID(p.get('requestId','')))
        except (ValueError,TypeError,AttributeError):
            raise HTTPException(400,'invalid_request_id')
        now=time.time()
        gb,cents=PACKAGES[sku]
        with database() as c:
            c.execute('BEGIN IMMEDIATE')
            existing=c.execute('SELECT * FROM orders WHERE user_id=? AND request_id=?',(uid,request_id)).fetchone()
            if existing:
                if existing['sku']!=sku or existing['method']!=method:
                    raise HTTPException(409,'request_id_reused')
                if existing['status']=='PENDING' and existing['payment_url']:
                    return public_order(existing)
                raise HTTPException(409,'order_already_created')
            if c.execute('SELECT COUNT(*) FROM orders WHERE user_id=? AND created>?',(uid,now-3600)).fetchone()[0]>=20:
                raise HTTPException(429,'sandbox_order_limit')
            ref='TOLF-SB-'+uuid.uuid4().hex
            c.execute('''INSERT INTO orders(reference,user_id,request_id,sku,gb,cents,method,locale,status,
                       terms_version,early_service,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                      (ref,uid,request_id,sku,gb,cents,method,locale,'CREATING',TERMS,1,now,now))
        amount=cents/100
        payment={'method':method,'amount':amount,'currency':'EUR'}
        if options:
            payment['methodOptions']=options
        payload={'merchantReference':ref,'returnUrl':ORIGIN+'/billing/?lang='+locale+'&sandboxOrder='+ref,
                 'notificationUrl':'https://api.tolf.is/billing/sandbox/notify',
                 'currency':'EUR','grandTotal':amount,'locale':locale,'expiresIn':30,
                 'lineItems':[{'name':'TOLF Sandbox '+sku+' GB (test only)','quantity':1,'finalPrice':amount}],
                 'payment':payment}
        try:
            result=provider('POST','/orders',payload)
            with database() as c:
                row=c.execute('SELECT * FROM orders WHERE reference=?',(ref,)).fetchone()
            provider_id=matching_order(result,row)
            url=result.get('paymentUrl','')
            parsed=urlparse(url)
            if parsed.scheme!='https' or parsed.hostname not in {'sandbox-stargate.montonio.com','sandbox-checkout.montonio.com','sandbox-gateway.montonio.com'} or parsed.username or parsed.port not in (None,443):
                raise HTTPException(502,'unsafe_payment_url')
            with database() as c:
                c.execute("UPDATE orders SET provider_uuid=?,payment_url=?,status=CASE WHEN status='PAID' THEN status ELSE 'PENDING' END,updated=? WHERE reference=?",
                          (provider_id,url,time.time(),ref))
                row=c.execute('SELECT * FROM orders WHERE reference=?',(ref,)).fetchone()
            return public_order(row)
        except Exception:
            with database() as c:
                c.execute("UPDATE orders SET status='UNKNOWN',updated=? WHERE reference=? AND status='CREATING'",(time.time(),ref))
            raise

    @app.post('/billing/sandbox/orders')
    async def create_order(request:Request):
        uid=allowed(request)
        payload=await read_payload(request)
        data=await run_in_threadpool(create,uid,payload)
        return JSONResponse(data,headers=HEADERS)

    @app.get('/billing/sandbox/orders/{reference}')
    def get_order(reference:str,request:Request):
        uid=allowed(request)
        with database() as c:
            row=c.execute('SELECT * FROM orders WHERE reference=? AND user_id=?',(reference,uid)).fetchone()
            if not row:
                raise HTTPException(404,'unknown_sandbox_order')
            now=time.time()
            # Limit provider polling even with multiple tabs/workers.
            should_check=bool(row['provider_uuid']) and now-row['last_provider_check']>=5
            if should_check:
                c.execute('UPDATE orders SET last_provider_check=? WHERE reference=?',(now,reference))
        if should_check:
            try:
                data=provider('GET','/orders/'+row['provider_uuid'])
                apply_status(data,'api')
            except HTTPException as exc:
                if exc.status_code!=502:
                    raise
        with database() as c:
            row=c.execute('SELECT * FROM orders WHERE reference=? AND user_id=?',(reference,uid)).fetchone()
        return JSONResponse(public_order(row),headers=HEADERS)

    @app.post('/billing/sandbox/notify')
    async def notify(request:Request):
        payload=await read_payload(request,False)
        data=decode_notification(payload.get('orderToken'))
        apply_status(data,'webhook')
        return JSONResponse({'received':True},headers=HEADERS)

    @app.post('/billing/sandbox/validate-return')
    async def validate_return(request:Request):
        uid=allowed(request)
        payload=await read_payload(request)
        data=decode_notification(payload.get('orderToken'))
        with database() as c:
            row=c.execute('SELECT * FROM orders WHERE reference=? AND user_id=?',(data.get('merchantReference'),uid)).fetchone()
        if not row:
            raise HTTPException(404,'unknown_sandbox_order')
        matching_order(data,row)
        # Return tokens are checked, but never create credits. Webhook or GET verification does that.
        return JSONResponse({'reference':row['reference'],'mode':'sandbox'},headers=HEADERS)
