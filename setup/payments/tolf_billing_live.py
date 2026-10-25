import tolf_billing_pricing as pricing
"""Montonio production pilot. Creation and account access require an admin role."""
import hashlib
import hmac
import json
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request as UrlRequest, build_opener
from urllib.error import HTTPError, URLError

import jwt
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from tolf_billing_sandbox import NoRedirect, TERMS, ORIGIN, HEADERS
from tolf_billing_records import clean_buyer, ISO

CONFIG = Path('/etc/tolf-payments/montonio-live.json')
BASE = 'https://stargate.montonio.com/api'
HOSTS = {'stargate.montonio.com', 'checkout.montonio.com', 'gateway.montonio.com'}
DB = None
AUTH = None

def config():
    try:
        cfg = json.loads(CONFIG.read_text())
        if cfg.get('environment') != 'production' or cfg.get('apiBase') != BASE or cfg.get('enabled') is not True:
            raise ValueError()
        if not all(isinstance(cfg.get(k), str) and cfg[k].strip() for k in ('accessKey', 'secretKey', 'storeUuid')):
            raise ValueError()
        uuid.UUID(cfg['storeUuid'])
        return cfg
    except (OSError, ValueError, TypeError):
        raise HTTPException(503, 'live_not_configured')

@contextmanager
def database():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    try:
        with c:
            yield c
    finally:
        c.close()

def initialize():
    with database() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS live_payment_orders(
          reference TEXT PRIMARY KEY, user_id TEXT NOT NULL, request_id TEXT NOT NULL,
          sku TEXT NOT NULL, gb INTEGER NOT NULL, cents INTEGER NOT NULL,
          method TEXT NOT NULL, locale TEXT NOT NULL, signature TEXT NOT NULL,
          status TEXT NOT NULL, provider_uuid TEXT UNIQUE, payment_url TEXT,
          created REAL NOT NULL, updated REAL NOT NULL, last_check REAL NOT NULL DEFAULT 0,
          UNIQUE(user_id,request_id));
        CREATE TABLE IF NOT EXISTS live_payment_credits(
          reference TEXT PRIMARY KEY REFERENCES live_payment_orders(reference),
          user_id TEXT NOT NULL, bytes INTEGER NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS live_payment_usage_baselines(
          user_id TEXT PRIMARY KEY, usage_bytes INTEGER NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS live_payment_events(
          id INTEGER PRIMARY KEY, reference TEXT NOT NULL, status TEXT NOT NULL,
          source TEXT NOT NULL, created REAL NOT NULL);
        ''')

def admin(request):
    uid = AUTH(request)
    with database() as c:
        if not c.execute('SELECT 1 FROM admin_roles WHERE user_id=?', (uid,)).fetchone():
            raise HTTPException(403, 'admin_required')
        if not c.execute('SELECT 1 FROM managed_users WHERE account_id=? AND deleted_at IS NULL', (uid,)).fetchone():
            raise HTTPException(403, 'active_account_required')
    return uid

def provider(method, path, payload=None):
    cfg = config()
    if not re.fullmatch(r'/stores/payment-methods|/orders(?:/[a-fA-F0-9-]{36})?', path):
        raise ValueError('Invalid provider path')
    now = int(time.time())
    token = jwt.encode({'accessKey': cfg['accessKey'], 'iat': now, 'exp': now+120, **(payload or {})}, cfg['secretKey'], algorithm='HS256')
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    body = None
    if method == 'GET':
        headers['Authorization'] = 'Bearer '+token
    else:
        body = json.dumps({'data': token}).encode()
    try:
        with build_opener(NoRedirect()).open(UrlRequest(BASE+path, data=body, headers=headers, method=method), timeout=18) as response:
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError()
            data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError()
        return data
    except HTTPError as e:
        raise HTTPException(502, 'live_provider_http_'+str(e.code)) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise HTTPException(502, 'live_provider_unavailable') from None

def payment_url(value):
    try:
        u = urlparse(value)
        if u.scheme == 'https' and u.hostname in HOSTS and not u.username and not u.password and u.port in (None,443):
            return value
    except (ValueError, TypeError):
        pass
    raise HTTPException(502, 'unsafe_payment_url')

def methods():
    data = provider('GET', '/stores/payment-methods')
    if data.get('uuid') != config()['storeUuid']:
        raise HTTPException(502, 'live_store_mismatch')
    raw = data.get('paymentMethods', {})
    result = {'billingCountries': sorted(ISO), 'methods': [m for m in ['cardPayments','paymentInitiation','applePay','googlePay'] if m in raw], 'banks': {}}
    for country, setup in raw.get('paymentInitiation', {}).get('setup', {}).items():
        banks = [{'code': b['code'], 'name': b['name']} for b in setup.get('paymentMethods', []) if 'EUR' in b.get('supportedCurrencies', [])]
        if banks:
            result['banks'][country] = banks
    return result

def public(row):
    result={'reference': row['reference'], 'package': row['sku'], 'gb': row['gb'], 'amount': row['cents']/100,
            'currency': 'EUR', 'status': row['status'], 'createdAt': row['created'], 'updatedAt': row['updated'],
            'mode': 'live', 'paymentUrl': row['payment_url'] if row['status']=='PENDING' else None, 'documents': []}
    result['method']=row['method']
    if row['method']=='bankTransfer':
        with database() as c:
            invoice=c.execute('SELECT number,confirmed_at FROM bank_transfer_invoices WHERE reference=?',(row['reference'],)).fetchone()
        if invoice:
            number=invoice['number'];result['bankInvoice']={'number':number,'paymentReference':number,'pdfUrl':'/billing/bank/invoices/'+number+'.pdf','receiptUrl':'/billing/bank/invoices/'+number+'/receipt.pdf' if invoice['confirmed_at'] else None}
    return result

def match(data, row):
    if row['method']=='bankTransfer':raise HTTPException(400,'wrong_payment_channel')
    cfg = config()
    try:
        amount = Decimal(str(data['grandTotal']))
        ok = amount.is_finite() and amount*100 == row['cents']
        order_id = str(uuid.UUID(data['uuid']))
    except (KeyError, ValueError, TypeError, InvalidOperation, AttributeError):
        raise HTTPException(400, 'order_mismatch')
    if not ok or data.get('currency') != 'EUR' or data.get('merchantReference') != row['reference']:
        raise HTTPException(400, 'order_mismatch')
    if data.get('storeUuid',cfg['storeUuid']) != cfg['storeUuid'] or data.get('accessKey',cfg['accessKey']) != cfg['accessKey']:
        raise HTTPException(400, 'wrong_store')
    if row['provider_uuid'] and order_id != row['provider_uuid']:
        raise HTTPException(400, 'order_uuid_mismatch')
    return order_id

def usage(c, uid):
    from tolf_traffic_policy import totals
    return totals(c, '1970-01-01T00:00:00+00:00').get(uid, 0)

def grant_credit(c,row):
    if c.execute('SELECT 1 FROM live_payment_credits WHERE reference=?',(row['reference'],)).fetchone():return
    if not c.execute('SELECT 1 FROM live_payment_usage_baselines WHERE user_id=?',(row['user_id'],)).fetchone():
        c.execute('INSERT INTO live_payment_usage_baselines VALUES(?,?,?)',(row['user_id'],usage(c,row['user_id']),time.time()))
    else:
        current=usage(c,row['user_id'])
        prior=c.execute('SELECT COALESCE(SUM(bytes),0) FROM live_payment_credits WHERE user_id=?',(row['user_id'],)).fetchone()[0]
        c.execute('UPDATE live_payment_usage_baselines SET usage_bytes=MAX(usage_bytes,?) WHERE user_id=?',(current-prior,row['user_id']))
    c.execute('INSERT OR IGNORE INTO live_payment_credits VALUES(?,?,?,?)',(row['reference'],row['user_id'],row['gb']*1_000_000_000,time.time()))

def apply_status(data, source):
    with database() as c:
        c.execute('BEGIN IMMEDIATE')
        row = c.execute('SELECT * FROM live_payment_orders WHERE reference=?', (data.get('merchantReference'),)).fetchone()
        if not row:
            raise HTTPException(404, 'unknown_live_order')
        oid = match(data, row)
        status = data.get('paymentStatus')
        if status not in {'PENDING','PAID','ABANDONED','VOIDED','DECLINED','CANCELLED','EXPIRED','AUTHORIZED','PARTIALLY_REFUNDED','REFUNDED'}:
            raise HTTPException(400, 'unknown_payment_status')
        rank = {'PAID':1,'PARTIALLY_REFUNDED':2,'REFUNDED':3}
        if rank.get(row['status'],0) > rank.get(status,0):
            status = row['status']
        if status == 'PAID':grant_credit(c,row)
        # Never keep spendable traffic for a refunded order. Partial refunds are
        # conservatively suspended for this pilot until a refund policy is configured.
        if status in {'REFUNDED','PARTIALLY_REFUNDED'}:
            c.execute('UPDATE live_payment_credits SET bytes=0 WHERE reference=?',(row['reference'],))
        c.execute('UPDATE live_payment_orders SET provider_uuid=?,status=?,updated=? WHERE reference=?',(oid,status,time.time(),row['reference']))
        c.execute('INSERT INTO live_payment_events(reference,status,source,created) VALUES(?,?,?,?)',(row['reference'],status,source,time.time()))
    return row['reference']

async def payload(request, origin=True):
    if origin and request.headers.get('origin') != ORIGIN:
        raise HTTPException(403, 'invalid_origin')
    if request.headers.get('content-type','').split(';')[0] != 'application/json':
        raise HTTPException(415, 'json_required')
    raw = b''
    async for chunk in request.stream():
        raw += chunk
        if len(raw) > 16000:
            raise HTTPException(413,'payload_too_large')
    try:
        data = json.loads(raw)
        if not isinstance(data,dict):
            raise ValueError()
        return data
    except (ValueError, TypeError):
        raise HTTPException(400, 'invalid_json')

def notification(token):
    cfg = config()
    if not isinstance(token,str) or len(token)>12000:
        raise HTTPException(400,'invalid_order_token')
    try:
        data = jwt.decode(token,cfg['secretKey'],algorithms=['HS256'],options={'require':['iat','exp','accessKey','uuid','merchantReference','currency','grandTotal','paymentStatus']},leeway=15)
    except jwt.InvalidTokenError:
        raise HTTPException(400,'invalid_order_token')
    if not hmac.compare_digest(str(data['accessKey']),cfg['accessKey']):
        raise HTTPException(400,'wrong_merchant')
    return data

def create(uid,p):
    if set(p)-{'package','method','locale','bankCountry','bankCode','requestId','termsVersion','acceptTerms','startNow','buyer','pricingVersion'}:
        raise HTTPException(400,'unexpected_checkout_fields')
    sku=p.get('package');method=p.get('method');locale=p.get('locale')
    pricing.require_version(p)
    gb,cents=pricing.quote(sku)
    if locale not in {'en','ru','lv'}:
        raise HTTPException(400,'invalid_package_or_locale')
    if p.get('termsVersion')!=TERMS or p.get('acceptTerms') is not True or p.get('startNow') is not True:
        raise HTTPException(400,'checkout_consent_required')
    buyer=clean_buyer(p.get('buyer'))
    try:
        request_id=str(uuid.UUID(p.get('requestId','')))
    except (ValueError,TypeError,AttributeError):
        raise HTTPException(400,'invalid_request_id')
    sig=hashlib.sha256(json.dumps(p,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    available=methods()
    if method not in available['methods']:
        raise HTTPException(400,'payment_method_unavailable')
    options={}
    if method=='paymentInitiation':
        if not any(b['code']==p.get('bankCode') for b in available['banks'].get(p.get('bankCountry'),[])):
            raise HTTPException(400,'invalid_bank')
        options={'preferredCountry':p['bankCountry'],'preferredProvider':p['bankCode']}
    now=time.time();ref='TOLF-LIVE-'+uuid.uuid4().hex
    with database() as c:
        c.execute('BEGIN IMMEDIATE')
        old=c.execute('SELECT * FROM live_payment_orders WHERE user_id=? AND request_id=?',(uid,request_id)).fetchone()
        if old:
            if old['signature']!=sig:
                raise HTTPException(409,'request_id_reused')
            if old['status']=='PENDING' and old['payment_url']:
                return public(old)
            raise HTTPException(409,'order_already_created')
        if c.execute('SELECT COUNT(*) FROM live_payment_orders WHERE user_id=? AND created>?',(uid,now-3600)).fetchone()[0]>=20:
            raise HTTPException(429,'live_order_limit')
        c.execute('''INSERT INTO live_payment_orders(reference,user_id,request_id,sku,gb,cents,method,locale,signature,status,created,updated)
                  VALUES(?,?,?,?,?,?,?,?,?,'CREATING',?,?)''',(ref,uid,request_id,sku,gb,cents,method,locale,sig,now,now))
    payment={'method':method,'amount':cents/100,'currency':'EUR'}
    if options:payment['methodOptions']=options
    order={'merchantReference':ref,'returnUrl':ORIGIN+'/billing/?lang='+locale+'&liveOrder='+ref,
           'notificationUrl':'https://api.tolf.is/billing/live/notify','currency':'EUR','grandTotal':cents/100,
           'locale':locale,'expiresIn':30,'lineItems':[{'name':'TOLF '+sku+' GB','quantity':1,'finalPrice':cents/100}],'payment':payment}
    if buyer:
        order['billingAddress']={'fullName':buyer['name'],'addressLine1':buyer['address'],'country':buyer['country']}
    try:
        data=provider('POST','/orders',order)
        with database() as c:
            row=c.execute('SELECT * FROM live_payment_orders WHERE reference=?',(ref,)).fetchone()
            oid=match(data,row);url=payment_url(data.get('paymentUrl'))
            c.execute("UPDATE live_payment_orders SET provider_uuid=?,payment_url=?,status=CASE WHEN status='CREATING' THEN 'PENDING' ELSE status END,updated=? WHERE reference=?",(oid,url,time.time(),ref))
            return public(c.execute('SELECT * FROM live_payment_orders WHERE reference=?',(ref,)).fetchone())
    except Exception:
        with database() as c:
            c.execute("UPDATE live_payment_orders SET status='UNKNOWN',updated=? WHERE reference=? AND status='CREATING'",(time.time(),ref))
        raise

def install(app,ns):
    global DB,AUTH
    DB=ns['DB'];AUTH=ns['authenticated_user_id'];initialize()

    @app.get('/billing/live/capabilities')
    def capabilities(request:Request):
        try:
            admin(request)
        except HTTPException as e:
            if e.status_code in (401,403):
                return JSONResponse({'mode':'preview','enabled':False},headers=HEADERS)
            raise
        try:
            config();ready=True
        except HTTPException:
            ready=False
        return JSONResponse({'mode':'live','enabled':ready,'livePayments':ready,'adminOnly':True,'termsVersion':TERMS,'pricingVersion':pricing.VERSION,'accountingExport':False},headers=HEADERS)

    @app.get('/billing/live/methods')
    def get_methods(request:Request):
        admin(request);return JSONResponse(methods(),headers=HEADERS)

    @app.get('/billing/live/account')
    def account(request:Request):
        uid=admin(request)
        with database() as c:
            rows=c.execute('SELECT * FROM live_payment_orders WHERE user_id=? ORDER BY created DESC LIMIT 30',(uid,)).fetchall()
            credits=c.execute('SELECT COALESCE(SUM(bytes),0) FROM live_payment_credits WHERE user_id=?',(uid,)).fetchone()[0]
            baseline=c.execute('SELECT usage_bytes FROM live_payment_usage_baselines WHERE user_id=?',(uid,)).fetchone()
            used=max(0,usage(c,uid)-baseline[0]) if baseline else 0
        return JSONResponse({'mode':'live','balanceBytes':max(0,credits-used),'creditedBytes':credits,'usedBytes':used,'orders':[public(r) for r in rows]},headers=HEADERS)

    @app.post('/billing/live/orders')
    async def create_order(request:Request):
        uid=admin(request);config();p=await payload(request)
        return JSONResponse(await run_in_threadpool(create,uid,p),headers=HEADERS)

    @app.get('/billing/live/orders/{reference}')
    def get_order(reference:str,request:Request,resume:bool=False):
        uid=admin(request);config()
        with database() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM live_payment_orders WHERE reference=? AND user_id=?',(reference,uid)).fetchone()
            if not row:raise HTTPException(404,'unknown_live_order')
            check=row['provider_uuid'] and time.time()-row['last_check']>=5
            if check:c.execute('UPDATE live_payment_orders SET last_check=? WHERE reference=?',(time.time(),reference))
        if check:
            data=provider('GET','/orders/'+row['provider_uuid']);apply_status(data,'api')
            if data.get('paymentStatus')=='PENDING' and data.get('paymentUrl'):
                url=payment_url(data['paymentUrl'])
                with database() as c:c.execute('UPDATE live_payment_orders SET payment_url=? WHERE reference=?',(url,reference))
        with database() as c:row=c.execute('SELECT * FROM live_payment_orders WHERE reference=? AND user_id=?',(reference,uid)).fetchone()
        return JSONResponse(public(row),headers=HEADERS)

    @app.post('/billing/live/notify')
    async def notify(request:Request):
        p=await payload(request,False);data=notification(p.get('orderToken'))
        with database() as c:
            row=c.execute('SELECT * FROM live_payment_orders WHERE reference=?',(data.get('merchantReference'),)).fetchone()
            if not row:raise HTTPException(404,'unknown_live_order')
            oid=match(data,row)
        # A signed webhook triggers independent provider verification. Neither
        # browser returns nor unverified notifications can credit traffic.
        fresh=await run_in_threadpool(provider,'GET','/orders/'+oid)
        await run_in_threadpool(apply_status,fresh,'webhook-verified')
        return JSONResponse({'received':True},headers=HEADERS)

    @app.post('/billing/live/validate-return')
    async def validate_return(request:Request):
        uid=admin(request);p=await payload(request);data=notification(p.get('orderToken'))
        with database() as c:
            row=c.execute('SELECT * FROM live_payment_orders WHERE reference=? AND user_id=?',(data.get('merchantReference'),uid)).fetchone()
            if not row:raise HTTPException(404,'unknown_live_order')
            match(data,row)
        return JSONResponse({'reference':row['reference'],'mode':'live'},headers=HEADERS)
