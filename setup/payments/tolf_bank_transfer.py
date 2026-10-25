"""Administrator-only pilot for invoiced bank transfers and atomic traffic credits."""
import hashlib
import json
import re
import sqlite3
import time
import uuid
from datetime import datetime,timedelta,date
from zoneinfo import ZoneInfo
from decimal import Decimal,InvalidOperation
from fastapi import HTTPException,Request
from fastapi.responses import JSONResponse,Response
from starlette.concurrency import run_in_threadpool
import tolf_billing_live as live
import tolf_billing_pricing as pricing
from tolf_billing_records import SELLER,ISO,clean_buyer
from tolf_bank_pdf import render
HEADERS=live.HEADERS
DEFAULT={'enabled':False,'beneficiary':'SIA Tolf','bankName':'Rietumu Bank','iban':'','bic':'','vatStatus':'unknown','vatNumber':'','dueDays':7}

def initialize():
    with live.database() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS bank_transfer_settings(id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL,revision INTEGER NOT NULL,updated REAL NOT NULL,actor TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS bank_transfer_counters(year INTEGER PRIMARY KEY,value INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS bank_transfer_invoices(number TEXT PRIMARY KEY,reference TEXT UNIQUE NOT NULL REFERENCES live_payment_orders(reference),snapshot TEXT NOT NULL,pdf BLOB NOT NULL,created REAL NOT NULL,due_date TEXT NOT NULL,transaction_id TEXT UNIQUE,received_date TEXT,confirmed_by TEXT,confirmed_at REAL,receipt_pdf BLOB);
        CREATE TABLE IF NOT EXISTS bank_transfer_audit(id INTEGER PRIMARY KEY,number TEXT,action TEXT NOT NULL,actor TEXT NOT NULL,data TEXT NOT NULL,created REAL NOT NULL);
        ''')
        c.execute('INSERT OR IGNORE INTO bank_transfer_settings VALUES(1,?,1,?,?)',(json.dumps(DEFAULT),time.time(),'installation'))

def text(value,limit=160):
    if not isinstance(value,str) or len(value)>limit or any(ord(ch)<32 for ch in value):raise HTTPException(400,'invalid_settings')
    return value.strip()

def validate_settings(p):
    if not isinstance(p,dict) or set(p)!=set(DEFAULT):raise HTTPException(400,'invalid_settings')
    if type(p['enabled']) is not bool or type(p['dueDays']) is not int or not 1<=p['dueDays']<=30:raise HTTPException(400,'invalid_settings')
    result=dict(p)
    for k in ['beneficiary','bankName','iban','bic','vatNumber']:result[k]=text(p[k],160)
    result['iban']=re.sub(r'\s+','',result['iban']).upper();result['bic']=result['bic'].upper();result['vatNumber']=result['vatNumber'].upper()
    if p['vatStatus'] not in {'unknown','non_registered','registered'}:raise HTTPException(400,'invalid_settings')
    if result['iban']:
        iban=result['iban']
        if not re.fullmatch(r'[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}',iban) or iban[:2] not in ISO or (iban.startswith('LV') and len(iban)!=21):raise HTTPException(400,'invalid_iban')
        numeric=''.join(str(ord(ch)-55) if ch.isalpha() else ch for ch in iban[4:]+iban[:4])
        if int(numeric)%97!=1:raise HTTPException(400,'invalid_iban')
    if result['bic'] and not re.fullmatch(r'[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?',result['bic']):raise HTTPException(400,'invalid_bic')
    if result['vatStatus']=='registered' and not re.fullmatch(r'LV[0-9]{11}',result['vatNumber']):raise HTTPException(400,'vat_number_required')
    if result['vatStatus']!='registered':result['vatNumber']=''
    if result['enabled'] and (not all(result[k] for k in ['beneficiary','bankName','iban','bic']) or result['vatStatus']=='unknown'):raise HTTPException(400,'bank_details_required')
    return result

def settings(c):
    row=c.execute('SELECT * FROM bank_transfer_settings WHERE id=1').fetchone()
    return json.loads(row['payload']),row['revision']

def current_settings():
    with live.database() as c:p,revision=settings(c)
    p=validate_settings(p)
    if not p['enabled']:raise HTTPException(503,'bank_details_required')
    return p,revision

def audit(c,number,action,actor,data):c.execute('INSERT INTO bank_transfer_audit(number,action,actor,data,created) VALUES(?,?,?,?,?)',(number,action,actor,json.dumps(data,ensure_ascii=False,sort_keys=True),time.time()))

def public_invoice(row):
    s=json.loads(row['snapshot'])
    return {'number':row['number'],'reference':row['reference'],'gb':s['gb'],'amount':s['cents']/100,'currency':'EUR','buyer':s['buyer'],'accountNumber':s['accountNumber'],'createdAt':row['created'],'dueDate':row['due_date'],'status':'PAID' if row['confirmed_at'] else 'PENDING','paymentReference':row['number'],'bank':s['bank'],'pdfUrl':'/billing/bank/invoices/'+row['number']+'.pdf','receiptUrl':'/billing/bank/invoices/'+row['number']+'/receipt.pdf' if row['confirmed_at'] else None,'receivedDate':row['received_date'],'transactionId':row['transaction_id']}

def create(uid,p):
    expected={'package','pricingVersion','termsVersion','acceptTerms','startNow','buyer','requestId','locale'}
    if set(p)-expected:raise HTTPException(400,'unexpected_checkout_fields')
    pricing.require_version(p);gb,cents=pricing.quote(p.get('package'))
    if p.get('termsVersion')!=live.TERMS or p.get('acceptTerms') is not True or p.get('startNow') is not True:raise HTTPException(400,'checkout_consent_required')
    if p.get('locale') not in {'ru','lv','en'}:raise HTTPException(400,'invalid_locale')
    buyer=clean_buyer(p.get('buyer'))
    if not buyer:raise HTTPException(400,'buyer_details_required')
    try:request_id=str(uuid.UUID(p.get('requestId','')))
    except (ValueError,TypeError,AttributeError):raise HTTPException(400,'invalid_request_id')
    signature=hashlib.sha256(json.dumps(p,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    with live.database() as c:
        c.execute('BEGIN IMMEDIATE')
        old=c.execute('SELECT * FROM live_payment_orders WHERE user_id=? AND request_id=?',(uid,request_id)).fetchone()
        if old:
            if old['method']!='bankTransfer' or old['signature']!=signature:raise HTTPException(409,'request_id_reused')
            row=c.execute('SELECT * FROM bank_transfer_invoices WHERE reference=?',(old['reference'],)).fetchone()
            return public_invoice(row)
        cfg,revision=settings(c);cfg=validate_settings(cfg)
        if not cfg['enabled']:raise HTTPException(503,'bank_details_required')
        if c.execute('SELECT COUNT(*) FROM live_payment_orders WHERE user_id=? AND created>?',(uid,time.time()-3600)).fetchone()[0]>=20:raise HTTPException(429,'live_order_limit')
        account=c.execute('SELECT number FROM managed_users WHERE account_id=? AND deleted_at IS NULL',(uid,)).fetchone()
        if not account:raise HTTPException(403,'active_account_required')
        now=time.time();day=datetime.fromtimestamp(now,ZoneInfo('Europe/Riga')).date();year=day.year
        c.execute('INSERT OR IGNORE INTO bank_transfer_counters VALUES(?,0)',(year,));c.execute('UPDATE bank_transfer_counters SET value=value+1 WHERE year=?',(year,))
        count=c.execute('SELECT value FROM bank_transfer_counters WHERE year=?',(year,)).fetchone()[0]
        number=f'TOLF-BT-{year}-{count:06d}';ref='TOLF-BANK-'+uuid.uuid4().hex
        due=(day+timedelta(days=cfg['dueDays'])).isoformat()
        snapshot={'number':number,'reference':ref,'accountNumber':account['number'],'gb':gb,'cents':cents,'created':now,'dueDate':due,'locale':p['locale'],'buyer':buyer,'seller':{**SELLER,'vatStatus':cfg['vatStatus'],'vatNumber':cfg['vatNumber']},'bank':{k:cfg[k] for k in ['beneficiary','bankName','iban','bic']},'settingsRevision':revision,'pricingVersion':pricing.VERSION,'termsVersion':live.TERMS,'acceptTerms':True,'startNow':True}
        pdf=render(snapshot)
        c.execute('''INSERT INTO live_payment_orders(reference,user_id,request_id,sku,gb,cents,method,locale,signature,status,created,updated) VALUES(?,?,?,?,?,?,'bankTransfer',?,?,'PENDING',?,?)''',(ref,uid,request_id,str(gb),gb,cents,p['locale'],signature,now,now))
        c.execute('INSERT INTO bank_transfer_invoices(number,reference,snapshot,pdf,created,due_date) VALUES(?,?,?,?,?,?)',(number,ref,json.dumps(snapshot,ensure_ascii=False,sort_keys=True),pdf,now,due))
        audit(c,number,'invoice.created',uid,{'gb':gb,'cents':cents,'settingsRevision':revision})
        return public_invoice(c.execute('SELECT * FROM bank_transfer_invoices WHERE number=?',(number,)).fetchone())

def confirm(number,actor,p):
    if set(p)!={'amount','currency','transactionId','receivedDate','confirmReceived'} or p.get('confirmReceived') is not True or p.get('currency')!='EUR':raise HTTPException(400,'invalid_confirmation')
    transaction=text(p.get('transactionId'),160)
    if not transaction:raise HTTPException(400,'transaction_required')
    try:
        amount=Decimal(str(p['amount']))
        if not amount.is_finite() or amount<=0 or amount*100!=(amount*100).to_integral_value():raise ValueError()
        cents=int(amount*100);received=date.fromisoformat(p['receivedDate'])
        if received>datetime.now(ZoneInfo('Europe/Riga')).date():raise ValueError()
    except (ValueError,TypeError,InvalidOperation):raise HTTPException(400,'invalid_confirmation')
    with live.database() as c:
        c.execute('BEGIN IMMEDIATE')
        invoice=c.execute('SELECT * FROM bank_transfer_invoices WHERE number=?',(number,)).fetchone()
        if not invoice:raise HTTPException(404,'unknown_bank_invoice')
        order=c.execute('SELECT * FROM live_payment_orders WHERE reference=?',(invoice['reference'],)).fetchone()
        if order['method']!='bankTransfer' or order['cents']!=cents:raise HTTPException(400,'payment_amount_mismatch')
        if invoice['confirmed_at']:
            if invoice['transaction_id']==transaction and invoice['received_date']==received.isoformat():return public_invoice(invoice)
            raise HTTPException(409,'invoice_already_paid')
        if order['status']!='PENDING':raise HTTPException(409,'invoice_not_pending')
        if c.execute('SELECT 1 FROM bank_transfer_invoices WHERE transaction_id=?',(transaction,)).fetchone():raise HTTPException(409,'transaction_already_used')
        now=time.time();receipt={'transactionId':transaction,'receivedDate':received.isoformat(),'confirmedAt':now,'confirmedBy':actor}
        pdf=render(json.loads(invoice['snapshot']),receipt=receipt)
        live.grant_credit(c,order)
        c.execute("UPDATE live_payment_orders SET status='PAID',updated=? WHERE reference=?",(now,order['reference']))
        c.execute('UPDATE bank_transfer_invoices SET transaction_id=?,received_date=?,confirmed_by=?,confirmed_at=?,receipt_pdf=? WHERE number=?',(transaction,received.isoformat(),actor,now,pdf,number))
        c.execute("INSERT INTO live_payment_events(reference,status,source,created) VALUES(?,'PAID','bank-confirmed',?)",(order['reference'],now))
        audit(c,number,'payment.confirmed',actor,{'transactionId':transaction,'receivedDate':received.isoformat(),'cents':cents})
        return public_invoice(c.execute('SELECT * FROM bank_transfer_invoices WHERE number=?',(number,)).fetchone())

def install(app,ns):
    initialize()
    @app.get('/billing/bank/capabilities')
    def capabilities(request:Request):
        try:live.admin(request)
        except HTTPException as e:
            if e.status_code in (401,403):return JSONResponse({'enabled':False,'admin':False},headers=HEADERS)
            raise
        try:current_settings();ready=True
        except HTTPException:ready=False
        return JSONResponse({'enabled':ready,'admin':True,'adminOnly':True,'pricingVersion':pricing.VERSION,'termsVersion':live.TERMS,'billingCountries':sorted(ISO)},headers=HEADERS)

    @app.post('/billing/bank/invoices')
    async def create_invoice(request:Request):
        uid=live.admin(request);p=await live.payload(request)
        return JSONResponse(await run_in_threadpool(create,uid,p),headers=HEADERS)

    @app.get('/billing/bank/invoices')
    def user_invoices(request:Request):
        uid=live.admin(request)
        with live.database() as c:rows=c.execute('SELECT i.* FROM bank_transfer_invoices i JOIN live_payment_orders o ON o.reference=i.reference WHERE o.user_id=? ORDER BY i.created DESC LIMIT 100',(uid,)).fetchall()
        return JSONResponse({'invoices':[public_invoice(r) for r in rows]},headers=HEADERS)

    def document(number,request,admin=False,receipt=False):
        uid=live.admin(request)
        with live.database() as c:
            if admin:row=c.execute('SELECT * FROM bank_transfer_invoices WHERE number=?',(number,)).fetchone()
            else:row=c.execute('SELECT i.* FROM bank_transfer_invoices i JOIN live_payment_orders o ON o.reference=i.reference WHERE i.number=? AND o.user_id=?',(number,uid)).fetchone()
        if not row or (receipt and not row['receipt_pdf']):raise HTTPException(404,'unknown_document')
        filename=number+('-paid' if receipt else '')+'.pdf'
        return Response(row['receipt_pdf'] if receipt else row['pdf'],media_type='application/pdf',headers={**HEADERS,'Content-Disposition':'attachment; filename="'+filename+'"','X-Content-Type-Options':'nosniff'})

    @app.get('/billing/bank/invoices/{number}.pdf')
    def invoice_pdf(number:str,request:Request):return document(number,request)

    @app.get('/billing/bank/invoices/{number}/receipt.pdf')
    def receipt_pdf(number:str,request:Request):return document(number,request,receipt=True)

    @app.get('/billing/bank/admin/settings')
    def get_settings(request:Request):
        live.admin(request)
        with live.database() as c:cfg,revision=settings(c)
        return JSONResponse({'settings':cfg,'revision':revision,'seller':SELLER},headers=HEADERS)

    @app.post('/billing/bank/admin/settings')
    async def save_settings(request:Request):
        actor=live.admin(request);p=await live.payload(request)
        if set(p)!={'settings','revision'} or type(p['revision']) is not int:raise HTTPException(400,'invalid_settings')
        cfg=validate_settings(p['settings'])
        with live.database() as c:
            c.execute('BEGIN IMMEDIATE');old,rev=settings(c)
            if rev!=p['revision']:raise HTTPException(409,'settings_changed')
            c.execute('UPDATE bank_transfer_settings SET payload=?,revision=revision+1,updated=?,actor=? WHERE id=1',(json.dumps(cfg,ensure_ascii=False),time.time(),actor))
            audit(c,None,'settings.updated',actor,{'old':old,'new':cfg,'revision':rev+1})
        return JSONResponse({'settings':cfg,'revision':rev+1,'seller':SELLER},headers=HEADERS)

    @app.get('/billing/bank/admin/invoices')
    def admin_invoices(request:Request,status:str='all',offset:int=0):
        live.admin(request)
        if status not in {'all','PENDING','PAID'} or not 0<=offset<=100000:raise HTTPException(400,'invalid_filter')
        where='' if status=='all' else 'WHERE '+('i.confirmed_at IS NULL' if status=='PENDING' else 'i.confirmed_at IS NOT NULL')
        with live.database() as c:
            total=c.execute('SELECT COUNT(*) FROM bank_transfer_invoices i '+where).fetchone()[0]
            rows=c.execute('SELECT i.* FROM bank_transfer_invoices i '+where+' ORDER BY i.created DESC LIMIT 100 OFFSET ?',(offset,)).fetchall()
        return JSONResponse({'invoices':[public_invoice(r) for r in rows],'total':total,'offset':offset},headers=HEADERS)

    @app.get('/billing/bank/admin/invoices/{number}.pdf')
    def admin_pdf(number:str,request:Request):return document(number,request,admin=True)

    @app.get('/billing/bank/admin/invoices/{number}/receipt.pdf')
    def admin_receipt(number:str,request:Request):return document(number,request,admin=True,receipt=True)

    @app.post('/billing/bank/admin/invoices/{number}/confirm')
    async def confirm_payment(number:str,request:Request):
        actor=live.admin(request);p=await live.payload(request)
        return JSONResponse(await run_in_threadpool(confirm,number,actor,p),headers=HEADERS)
