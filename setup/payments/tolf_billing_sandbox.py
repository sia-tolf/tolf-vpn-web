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
from fastapi import HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, Response
import tolf_billing_records as records
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
        records.initialize(c)
        c.execute('BEGIN IMMEDIATE')
        for row in c.execute('SELECT o.* FROM orders o JOIN credits p ON p.order_reference=o.reference').fetchall():
            records.record_paid(c,row)
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
        if status not in {'PENDING','PAID','ABANDONED','VOIDED','DECLINED','CANCELLED','EXPIRED','AUTHORIZED','PARTIALLY_REFUNDED','REFUNDED'}:
            raise HTTPException(400,'unknown_payment_status')
        # Late pending/failed notifications cannot reverse a paid order.
        paid_states={'PAID','PARTIALLY_REFUNDED','REFUNDED'}
        rank={'PAID':1,'PARTIALLY_REFUNDED':2,'REFUNDED':3}
        if row['status'] in paid_states and rank.get(status,0)<rank[row['status']]:
            status=row['status']
        if status in paid_states:
            c.execute('INSERT OR IGNORE INTO credits VALUES (?,?,?,?)',
                      (reference,row['user_id'],row['gb']*1_000_000_000,time.time()))
        records.evidence(c,reference,data,source)
        records.record_paid(c,row)
        records.record_refunds(c,row,data,source)
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
    result={'reference':row['reference'],'package':row['sku'],'gb':row['gb'],
            'amount':row['cents']/100,'currency':'EUR','status':row['status'],
            'createdAt':row['created'],'updatedAt':row['updated'],
            'mode':'sandbox','paymentUrl':row['payment_url'] if row['status']=='PENDING' else None}
    with database() as c:
        return records.enrich(c,result)

def install(app,ns):
    initialize()
    def account_label(uid):
        with sqlite3.connect(ns['DB']) as c:
            row=c.execute('''SELECT COALESCE(NULLIF(m.vpn_username,''),NULLIF(p.username,'')),m.number
                             FROM managed_users m LEFT JOIN account_passwords p ON p.user_id=m.account_id
                             WHERE m.account_id=? AND m.deleted_at IS NULL''',(uid,)).fetchone()
        if not row:
            return ''
        return row[0] or 'TOLF #'+str(row[1])

    with database() as c:
        rows=c.execute('SELECT reference,user_id FROM orders WHERE reference NOT IN (SELECT order_reference FROM order_identity)').fetchall()
        for row in rows:
            c.execute('INSERT OR IGNORE INTO order_identity VALUES(?,?)',(row['reference'],account_label(row['user_id'])))
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

    def require_admin(request):
        uid=allowed(request)
        with sqlite3.connect(ns['DB']) as c:
            if not c.execute('SELECT 1 FROM admin_roles WHERE user_id=?',(uid,)).fetchone():
                raise HTTPException(403,'admin_required')
        return uid

    def enabled_methods():
        with methods_lock:
            if time.time()<cache['until']:
                return cache['data']
            data=provider('GET','/stores/payment-methods')
            if data.get('uuid')!=config()['storeUuid']:
                raise HTTPException(502,'sandbox_store_mismatch')
            raw=data.get('paymentMethods',{})
            result={'billingCountries':sorted(records.ISO),'methods':[m for m in ['cardPayments','paymentInitiation','applePay','googlePay'] if m in raw],
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
        try:
            require_admin(request)
            admin=True
        except HTTPException:
            admin=False
        return JSONResponse({'mode':'sandbox','enabled':True,'termsVersion':TERMS,'livePayments':False,
                             'accountingExport':admin,'taxCountryStatus':'unresolved'},headers=HEADERS)

    @app.get('/billing/sandbox/methods')
    def methods(request:Request):
        allowed(request)
        return JSONResponse(enabled_methods(),headers=HEADERS)

    @app.get('/billing/sandbox/account')
    def account(request:Request):
        uid=allowed(request)
        with database() as c:
            rows=c.execute("SELECT * FROM orders WHERE user_id=? AND status NOT IN ('ABANDONED','VOIDED','DECLINED','CANCELLED','EXPIRED') ORDER BY created DESC LIMIT 30",(uid,)).fetchall()
            balance=c.execute('SELECT COALESCE(SUM(remaining_bytes),0) FROM package_lots WHERE user_id=?',(uid,)).fetchone()[0]
        return JSONResponse({'mode':'sandbox','testBalanceBytes':balance,'orders':[public_order(x) for x in rows]},headers=HEADERS)

    @app.post('/billing/sandbox/orders/{reference}/billing-document')
    async def billing_document(reference:str,request:Request):
        uid=allowed(request)
        p=await read_payload(request)
        if set(p)!={'buyer'}:
            raise HTTPException(400,'unexpected_document_fields')
        buyer=records.clean_buyer(p.get('buyer'))
        with database() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM orders WHERE reference=? AND user_id=?',(reference,uid)).fetchone()
            if not row:
                raise HTTPException(404,'unknown_sandbox_order')
            number=records.request_billing_document(c,row,buyer)
        return JSONResponse({'number':number,'mode':'sandbox'},headers=HEADERS)

    @app.get('/billing/sandbox/documents/{number}.pdf')
    def document(number:str,request:Request):
        uid=allowed(request)
        with database() as c:
            doc=c.execute('SELECT d.number FROM documents d JOIN orders o ON o.reference=d.order_reference WHERE d.number=? AND o.user_id=?',
                          (number,uid)).fetchone()
            if not doc:
                raise HTTPException(404,'unknown_document')
            pdf=records.document_pdf(c,number)
        return Response(pdf,media_type='application/pdf',
                        headers={**HEADERS,'Content-Disposition':'attachment; filename="'+number+'.pdf"','X-Content-Type-Options':'nosniff'})

    @app.get('/billing/sandbox/admin/export.csv')
    def accounting_export(request:Request,month:str,kind:str='purchases'):
        require_admin(request)
        with database() as c:
            result=records.export(c,month,kind)
        return Response(result,media_type='text/csv; charset=utf-8',
                        headers={**HEADERS,'Content-Disposition':'attachment; filename="tolf-sandbox-'+month+'-'+kind+'.csv"'})

    @app.get('/billing/sandbox/admin/export.pdf')
    def accounting_export_pdf(request:Request,month:str,kind:str='purchases',locale:str='en'):
        require_admin(request)
        with database() as c:
            c.execute('BEGIN')
            result=records.export_pdf(c,month,kind,locale)
        return Response(result,media_type='application/pdf',
                        headers={**HEADERS,'Content-Disposition':'attachment; filename="tolf-sandbox-'+month+'-'+kind+'.pdf"',
                                 'X-Content-Type-Options':'nosniff'})

    @app.post('/billing/sandbox/admin/usage')
    async def test_usage(request:Request):
        require_admin(request)
        p=await read_payload(request)
        if set(p)!={'userId','eventId','bytes'} or not isinstance(p['userId'],str) or len(p['userId'])>100:
            raise HTTPException(400,'invalid_usage_request')
        with database() as c:
            c.execute('BEGIN IMMEDIATE')
            records.consume(c,p['userId'],p['eventId'],p['bytes'])
        return JSONResponse({'mode':'sandbox','recorded':True},headers=HEADERS)

    def create(uid,p):
        expected={'package','method','locale','bankCountry','bankCode','requestId','termsVersion','acceptTerms','startNow','buyer'}
        if set(p)-expected:
            raise HTTPException(400,'unexpected_checkout_fields')
        buyer=records.clean_buyer(p.get('buyer'))
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
                previous=c.execute('SELECT buyer_json FROM checkout_details WHERE order_reference=?',(existing['reference'],)).fetchone()
                previous_buyer=json.loads(previous[0]) if previous else {}
                if existing['sku']!=sku or existing['method']!=method or previous_buyer!=buyer:
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
            c.execute('INSERT INTO order_identity VALUES(?,?)',(ref,account_label(uid)))
            c.execute('INSERT INTO checkout_details VALUES(?,?,?,?)',(ref,json.dumps(buyer,ensure_ascii=False,sort_keys=True),
                       p.get('bankCountry') if method=='paymentInitiation' else None,
                       p.get('bankCode') if method=='paymentInitiation' else None))
            if buyer:
                records.evidence(c,ref,{'billingAddress':{'country':buyer['country']}},'checkout')
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
    def get_order(reference:str,request:Request,resume:bool=False):
        uid=allowed(request)
        with database() as c:
            row=c.execute('SELECT * FROM orders WHERE reference=? AND user_id=?',(reference,uid)).fetchone()
            if not row:
                raise HTTPException(404,'unknown_sandbox_order')
            now=time.time()
            # Limit provider polling even with multiple tabs/workers.
            should_check=bool(row['provider_uuid']) and (resume or now-row['last_provider_check']>=5)
            if should_check:
                c.execute('UPDATE orders SET last_provider_check=? WHERE reference=?',(now,reference))
        if should_check:
            try:
                data=provider('GET','/orders/'+row['provider_uuid'])
                apply_status(data,'api')
                if resume and data.get('paymentStatus')=='PENDING':
                    fresh_url=data.get('paymentUrl')
                    parsed=urlparse(fresh_url or '')
                    if fresh_url and (parsed.scheme!='https' or parsed.hostname not in {'sandbox-stargate.montonio.com','sandbox-checkout.montonio.com','sandbox-gateway.montonio.com'} or parsed.username or parsed.password or parsed.port not in (None,443)):
                        raise HTTPException(502,'unsafe_payment_url')
                    with database() as c:
                        c.execute("UPDATE orders SET payment_url=? WHERE reference=? AND status='PENDING'",(fresh_url,reference))
            except HTTPException as exc:
                if resume or exc.status_code!=502:
                    raise
        with database() as c:
            row=c.execute('SELECT * FROM orders WHERE reference=? AND user_id=?',(reference,uid)).fetchone()
        return JSONResponse(public_order(row),headers=HEADERS)

    def refresh_provider(reference):
        with database() as c:
            row=c.execute('SELECT provider_uuid FROM orders WHERE reference=?',(reference,)).fetchone()
        if row and row[0]:
            try:
                apply_status(provider('GET','/orders/'+row[0]),'api')
            except HTTPException:
                # Preserve the signed status; owner GET can retry reconciliation.
                pass

    @app.post('/billing/sandbox/notify')
    async def notify(request:Request,background_tasks:BackgroundTasks):
        payload=await read_payload(request,False)
        data=decode_notification(payload.get('orderToken'))
        reference=apply_status(data,'webhook')
        if data.get('paymentStatus') in {'PAID','PARTIALLY_REFUNDED','REFUNDED'}:
            background_tasks.add_task(refresh_provider,reference)
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
