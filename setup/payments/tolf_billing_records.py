"""Immutable sandbox receipts and a separate test package ledger. Never live accounting."""
import csv
import io
import json
import re
import time
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from html import escape

import pycountry
from fastapi import HTTPException
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

SELLER = {'name':'SIA “Tolf”','registration':'40203551237',
          'address':'Brīvības iela 101-6, Rīga, LV-1001, Latvia',
          'email':'tolf@velbnk.is','phone':'+371 26165804'}
POLICY = 'sandbox-tax-unconfigured-20261022'
ISO = {x.alpha_2 for x in pycountry.countries}

def initialize(c):
    c.executescript("""
    CREATE TABLE IF NOT EXISTS checkout_details(
        order_reference TEXT PRIMARY KEY, buyer_json TEXT NOT NULL, bank_country TEXT, bank_code TEXT);
    CREATE TABLE IF NOT EXISTS country_evidence(
        order_reference TEXT NOT NULL, field TEXT NOT NULL, country TEXT NOT NULL,
        provenance TEXT NOT NULL, first_seen REAL NOT NULL, last_seen REAL NOT NULL,
        PRIMARY KEY(order_reference,field,country,provenance));
    CREATE TABLE IF NOT EXISTS documents(
        number TEXT PRIMARY KEY, order_reference TEXT NOT NULL, kind TEXT NOT NULL,
        external_id TEXT UNIQUE, snapshot_json TEXT NOT NULL, pdf BLOB NOT NULL, created REAL NOT NULL,
        UNIQUE(order_reference,kind,external_id));
    CREATE UNIQUE INDEX IF NOT EXISTS one_purchase_document ON documents(order_reference) WHERE kind='purchase';
    CREATE TABLE IF NOT EXISTS package_lots(
        order_reference TEXT PRIMARY KEY, user_id TEXT NOT NULL, total_bytes INTEGER NOT NULL,
        remaining_bytes INTEGER NOT NULL, cents INTEGER NOT NULL, created REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS ledger_events(
        event_key TEXT PRIMARY KEY, user_id TEXT NOT NULL, order_reference TEXT NOT NULL,
        kind TEXT NOT NULL, bytes INTEGER NOT NULL, cents INTEGER NOT NULL, created REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS provider_fees(
        intent_id TEXT PRIMARY KEY, order_reference TEXT NOT NULL, fee_cents INTEGER,
        currency TEXT, status TEXT NOT NULL, observed REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS provider_refunds(
        refund_id TEXT PRIMARY KEY, order_reference TEXT NOT NULL, cents INTEGER NOT NULL, observed REAL NOT NULL);
    """)
    for name,filename in [('Tolf','DejaVuSans.ttf'),('TolfBold','DejaVuSans-Bold.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name,'/usr/share/fonts/truetype/dejavu/'+filename))

def clean_buyer(value):
    if value is None:
        return {}
    if not isinstance(value,dict) or set(value)-{'kind','name','address','country','registration','vatNumber'}:
        raise HTTPException(400,'invalid_buyer')
    if value.get('kind') not in {'individual','company'}:
        raise HTTPException(400,'invalid_buyer')
    result={'kind':value['kind']}
    for field,limit in [('name',160),('address',400),('country',2),('registration',50),('vatNumber',50)]:
        v=value.get(field,'')
        if not isinstance(v,str) or len(v)>limit or any(ord(ch)<32 for ch in v):
            raise HTTPException(400,'invalid_buyer')
        result[field]=v.strip()
    if not result['name'] or not result['address'] or result['country'] not in ISO:
        raise HTTPException(400,'buyer_details_required')
    if result['kind']=='company' and not result['registration']:
        raise HTTPException(400,'company_registration_required')
    return result

def evidence(c,reference,data,source):
    # preferredCountry is gateway routing, not an independently established payer country.
    # billingAddress is merchant/customer supplied, even when echoed by authenticated GET.
    now=time.time()
    country=(data.get('billingAddress') or {}).get('country') if isinstance(data.get('billingAddress'),dict) else None
    if isinstance(country,str) and country in ISO:
        c.execute("""INSERT INTO country_evidence VALUES(?,?,?,?,?,?)
                     ON CONFLICT(order_reference,field,country,provenance) DO UPDATE SET last_seen=excluded.last_seen""",
                  (reference,'billingAddress.country',country,'merchant_or_customer_declared',now,now))
    for intent in data.get('paymentIntents') or []:
        if not isinstance(intent,dict):
            continue
        metadata=intent.get('paymentMethodMetadata') or {}
        country=metadata.get('preferredCountry') if isinstance(metadata,dict) else None
        if isinstance(country,str) and country in ISO:
            c.execute("""INSERT INTO country_evidence VALUES(?,?,?,?,?,?)
                         ON CONFLICT(order_reference,field,country,provenance) DO UPDATE SET last_seen=excluded.last_seen""",
                      (reference,'paymentMethodMetadata.preferredCountry',country,'gateway_selection_not_tax_evidence',now,now))
        # No guessing from BIC, bank name, receiving merchant IBAN, or card pricing group.
        # Add independently verified payer fields only after their semantics are documented.
        if source=='api' and isinstance(intent.get('uuid'),str) and len(intent['uuid'])<=100:
            fee=intent.get('serviceFee')
            if fee is not None:
                fee=Decimal(str(fee))
                if not fee.is_finite() or fee<0 or fee*100!=(fee*100).to_integral_value():
                    continue
                fee=int(fee*100)
            cur=intent.get('serviceFeeCurrency')
            if cur is not None and cur not in ISO and not re.fullmatch('[A-Z]{3}',str(cur)):
                continue
            c.execute("""INSERT INTO provider_fees VALUES(?,?,?,?,?,?)
                         ON CONFLICT(intent_id) DO UPDATE SET fee_cents=COALESCE(excluded.fee_cents,fee_cents),
                         status=excluded.status,observed=excluded.observed""",
                      (intent['uuid'],reference,fee,cur,str(intent.get('status',''))[:32],now))

def country_info(c,reference):
    rows=c.execute('SELECT field,country,provenance FROM country_evidence WHERE order_reference=? ORDER BY field,country',(reference,)).fetchall()
    return {'country':None,'status':'unresolved','evidence':[dict(x) for x in rows]}

LABELS={
'ru':{'title':'Подтверждение покупки','requested':'Подтверждение покупки с реквизитами','correction':'Подтверждение возврата',
      'test':'ТЕСТОВЫЙ ДОКУМЕНТ - SANDBOX','note':'Реальные деньги не списывались. Документ не является налоговым счётом.',
      'seller':'Продавец','buyer':'Покупатель','account':'Аккаунт TOLF','date':'Дата (UTC)','order':'Заказ',
      'service':'Предоплаченный пакет VPN-трафика','total':'Итого','refund':'Возврат','tax':'Режим НДС: не настроен для реальных продаж.',
      'end':'Начисление пакета и бухгалтерское признание выручки учитываются раздельно.'},
'en':{'title':'Purchase confirmation','requested':'Purchase confirmation with billing details','correction':'Refund confirmation',
      'test':'TEST DOCUMENT - SANDBOX','note':'No real money was charged. This is not a VAT invoice.',
      'seller':'Seller','buyer':'Buyer','account':'TOLF account','date':'Date (UTC)','order':'Order',
      'service':'Prepaid VPN traffic package','total':'Total','refund':'Refund','tax':'VAT treatment: not configured for live sales.',
      'end':'Package crediting and accounting revenue recognition are recorded separately.'},
'lv':{'title':'Pirkuma apstiprinājums','requested':'Pirkuma apstiprinājums ar rekvizītiem','correction':'Atmaksas apstiprinājums',
      'test':'TESTA DOKUMENTS - SANDBOX','note':'Reāla nauda netika iekasēta. Šis nav PVN rēķins.',
      'seller':'Pārdevējs','buyer':'Pircējs','account':'TOLF konts','date':'Datums (UTC)','order':'Pasūtījums',
      'service':'Priekšapmaksas VPN datu paka','total':'Kopā','refund':'Atmaksa','tax':'PVN režīms: nav konfigurēts reālai pārdošanai.',
      'end':'Pakas ieskaitīšana un grāmatvedības ieņēmumu atzīšana tiek uzskaitīta atsevišķi.'}}

def render_pdf(snapshot):
    x=LABELS[snapshot['locale']]
    output=io.BytesIO()
    doc=SimpleDocTemplate(output,pagesize=(595.28,841.89),rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=40,
                          title=x['title']+' '+snapshot['number'],author='SIA Tolf',invariant=1)
    normal=ParagraphStyle('normal',fontName='Tolf',fontSize=10,leading=15,textColor=colors.HexColor('#202124'),wordWrap='CJK')
    title=ParagraphStyle('title',parent=normal,fontName='TolfBold',fontSize=21,leading=27,spaceAfter=12)
    muted=ParagraphStyle('muted',parent=normal,fontSize=9,textColor=colors.HexColor('#666666'))
    def para(v,style=normal): return Paragraph(escape(str(v)),style)
    def block(label,lines):
        return [para(label,ParagraphStyle('label',parent=normal,fontName='TolfBold')),*[para(v) for v in lines if v],Spacer(1,14)]
    story=[para('TOLF',title),para(x['test'],ParagraphStyle('test',parent=normal,textColor=colors.HexColor('#244a85'),fontName='TolfBold')),
           Spacer(1,16),para(x['correction'] if snapshot['kind']=='refund' else x['requested'] if snapshot['buyer'] else x['title'],title),
           para(snapshot['number']),para(x['date']+': '+datetime.fromtimestamp(snapshot['created'],timezone.utc).strftime('%Y-%m-%d %H:%M:%S')),
           Spacer(1,20)]
    s=snapshot['seller']
    story+=block(x['seller'],[s['name'],s['registration'],s['address'],s['email']+' | '+s['phone']])
    b=snapshot['buyer']
    story+=block(x['buyer'],[b.get('name',x['account']+' '+snapshot['accountReference']),b.get('registration'),b.get('vatNumber'),b.get('address'),b.get('country')])
    story += [para(x['order']+': '+snapshot['orderReference'],muted),Spacer(1,18)]
    amount=f"{snapshot['cents']/100:.2f} EUR"
    rows=[[para(x['refund'] if snapshot['kind']=='refund' else x['service']),para('' if snapshot['kind']=='refund' else str(snapshot['gb'])+' GB'),para(amount)]]
    table=Table(rows,colWidths=[315,75,121.28])
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f0f4fa')),('VALIGN',(0,0),(-1,-1),'TOP'),
                               ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),
                               ('TOPPADDING',(0,0),(-1,-1),15),('BOTTOMPADDING',(0,0),(-1,-1),15)]))
    story += [table,Spacer(1,16),para(x['total']+': '+amount,ParagraphStyle('total',parent=title,alignment=TA_RIGHT,fontSize=17)),
              Spacer(1,12),para(x['note'],muted),para(x['tax'],muted),Spacer(1,12),para(x['end'],muted)]
    if snapshot.get('originalDocument'):
        story += [Spacer(1,12),para(snapshot['originalDocument'],muted)]
    doc.build(story)
    return output.getvalue()

def create_document(c,row,kind='purchase',external_id=None,cents=None):
    existing=c.execute('SELECT number FROM documents WHERE order_reference=? AND kind=? AND external_id IS ?',
                       (row['reference'],kind,external_id)).fetchone()
    if existing: return existing[0]
    now=time.time()
    year=datetime.fromtimestamp(now,timezone.utc).year
    prefix='TOLF-SB-'+('CR-' if kind=='refund' else '')+str(year)+'-'
    seq=c.execute('SELECT COUNT(*)+1 FROM documents WHERE number LIKE ?',(prefix+'%',)).fetchone()[0]
    number=prefix+str(seq).zfill(6)
    details=c.execute('SELECT buyer_json FROM checkout_details WHERE order_reference=?',(row['reference'],)).fetchone()
    buyer=json.loads(details[0]) if details else {}
    paid=c.execute('SELECT created FROM credits WHERE order_reference=?',(row['reference'],)).fetchone()
    original=c.execute("SELECT number FROM documents WHERE order_reference=? AND kind='purchase'",(row['reference'],)).fetchone()
    snapshot={'version':1,'number':number,'kind':kind,'created':paid[0] if kind=='purchase' and paid else now,
              'issuedAt':now,'locale':row['locale'],'seller':dict(SELLER),'buyer':buyer,
              'accountReference':row['user_id'],'orderReference':row['reference'],'gb':row['gb'],
              'cents':row['cents'] if cents is None else cents,'currency':'EUR','taxPolicy':POLICY,
              'taxCountry':None,'vatRate':None,'vatCents':None,'environment':'sandbox',
              'originalDocument':original[0] if kind=='refund' and original else None}
    encoded=json.dumps(snapshot,ensure_ascii=False,sort_keys=True)
    c.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?)',(number,row['reference'],kind,external_id,encoded,render_pdf(snapshot),now))
    return number

def record_paid(c,row):
    ref=row['reference']
    credit=c.execute('SELECT created FROM credits WHERE order_reference=?',(ref,)).fetchone()
    if not credit: return
    c.execute('INSERT OR IGNORE INTO package_lots VALUES(?,?,?,?,?,?)',
              (ref,row['user_id'],row['gb']*10**9,row['gb']*10**9,row['cents'],credit[0]))
    c.execute('INSERT OR IGNORE INTO ledger_events VALUES(?,?,?,?,?,?,?)',
              ('purchase:'+ref,row['user_id'],ref,'purchase',row['gb']*10**9,row['cents'],credit[0]))
    create_document(c,row)

def record_refunds(c,row,data,source):
    # Only authenticated provider GET supplies complete refund details; a return URL never does.
    if source!='api': return
    for refund in data.get('refunds') or []:
        if not isinstance(refund,dict) or refund.get('status')!='SUCCESSFUL' or refund.get('currency')!='EUR': continue
        rid=refund.get('uuid')
        if not isinstance(rid,str) or not re.fullmatch('[a-fA-F0-9-]{36}',rid): continue
        amount=Decimal(str(refund.get('amount')))
        if not amount.is_finite() or amount<=0 or amount*100!=(amount*100).to_integral_value(): continue
        cents=int(amount*100)
        if c.execute('SELECT 1 FROM provider_refunds WHERE refund_id=?',(rid,)).fetchone(): continue
        prior=c.execute('SELECT COALESCE(SUM(cents),0) FROM provider_refunds WHERE order_reference=?',(row['reference'],)).fetchone()[0]
        if prior+cents>row['cents']: raise HTTPException(400,'refund_exceeds_payment')
        lot=c.execute('SELECT * FROM package_lots WHERE order_reference=?',(row['reference'],)).fetchone()
        if not lot: continue
        # Cumulative rounding ensures a complete refund revokes the complete unspent package.
        target=(lot['total_bytes']*(prior+cents))//row['cents']
        previous=(lot['total_bytes']*prior)//row['cents']
        revoke=min(lot['remaining_bytes'],target-previous)
        now=time.time()
        c.execute('INSERT INTO provider_refunds VALUES(?,?,?,?)',(rid,row['reference'],cents,now))
        c.execute('UPDATE package_lots SET remaining_bytes=remaining_bytes-? WHERE order_reference=?',(revoke,row['reference']))
        c.execute('INSERT INTO ledger_events VALUES(?,?,?,?,?,?,?)',('refund:'+rid,row['user_id'],row['reference'],'refund',-revoke,-cents,now))
        create_document(c,row,'refund',rid,-cents)

def consume(c,uid,event_id,byte_count):
    if not isinstance(event_id,str) or not re.fullmatch('[A-Za-z0-9_-]{8,80}',event_id):
        raise HTTPException(400,'invalid_usage_id')
    if type(byte_count) is not int or byte_count<=0 or byte_count>10**15:
        raise HTTPException(400,'invalid_usage_bytes')
    # Prefix contains owner. One request may span multiple lots; group deduplication is separate.
    c.execute('CREATE TABLE IF NOT EXISTS usage_requests(user_id TEXT,event_id TEXT,bytes INTEGER,PRIMARY KEY(user_id,event_id))')
    existing=c.execute('SELECT bytes FROM usage_requests WHERE user_id=? AND event_id=?',(uid,event_id)).fetchone()
    if existing:
        if existing[0]!=byte_count: raise HTTPException(409,'usage_id_reused')
        return
    lots=c.execute('SELECT * FROM package_lots WHERE user_id=? AND remaining_bytes>0 ORDER BY created,order_reference',(uid,)).fetchall()
    if sum(x['remaining_bytes'] for x in lots)<byte_count: raise HTTPException(409,'insufficient_test_balance')
    remaining=byte_count
    for lot in lots:
        used=min(remaining,lot['remaining_bytes'])
        if not used: break
        c.execute('UPDATE package_lots SET remaining_bytes=remaining_bytes-? WHERE order_reference=?',(used,lot['order_reference']))
        c.execute('INSERT INTO ledger_events VALUES(?,?,?,?,?,?,?)',
                  ('usage:'+uid+':'+event_id+':'+lot['order_reference'],uid,lot['order_reference'],'usage',-used,0,time.time()))
        remaining-=used
    c.execute('INSERT INTO usage_requests VALUES(?,?,?)',(uid,event_id,byte_count))

def enrich(c,result):
    ref=result['reference']
    result['documents']=[{'number':r['number'],'kind':r['kind']} for r in c.execute('SELECT number,kind FROM documents WHERE order_reference=? ORDER BY created',(ref,))]
    lot=c.execute('SELECT total_bytes,remaining_bytes FROM package_lots WHERE order_reference=?',(ref,)).fetchone()
    result['remainingBytes']=lot['remaining_bytes'] if lot else None
    result['countryEvidence']=country_info(c,ref)
    return result

def export(c,month,kind):
    if not re.fullmatch(r'20[0-9]{2}-(0[1-9]|1[0-2])',month): raise HTTPException(400,'invalid_month')
    year,mo=map(int,month.split('-'))
    start=datetime(year,mo,1,tzinfo=timezone.utc).timestamp()
    end=datetime(year+int(mo==12),1 if mo==12 else mo+1,1,tzinfo=timezone.utc).timestamp()
    out=io.StringIO(newline='')
    w=csv.writer(out)
    def safe(v):
        # Spreadsheet formula injection protection for customer-supplied strings.
        return "'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v
    if kind=='purchases':
        w.writerow(['mode','document','issued_utc','paid_utc','order','buyer_name','buyer_registration','gb','gross_eur','vat_policy','tax_country','country_status'])
        for r in c.execute('SELECT * FROM documents WHERE created>=? AND created<? ORDER BY created',(start,end)):
            d=json.loads(r['snapshot_json'])
            w.writerow([safe(v) for v in ['sandbox',r['number'],datetime.fromtimestamp(r['created'],timezone.utc).isoformat(),
                         datetime.fromtimestamp(d['created'],timezone.utc).isoformat(),r['order_reference'],d['buyer'].get('name',''),
                         d['buyer'].get('registration',''),d['gb'],f"{d['cents']/100:.2f}",d['taxPolicy'],'','unresolved']])
    elif kind=='movements':
        w.writerow(['mode','event','account','order','kind','bytes','eur','utc'])
        for r in c.execute('SELECT * FROM ledger_events WHERE created>=? AND created<? ORDER BY created,event_key',(start,end)):
            w.writerow(['sandbox',r['event_key'],r['user_id'],r['order_reference'],r['kind'],r['bytes'],f"{r['cents']/100:.2f}",datetime.fromtimestamp(r['created'],timezone.utc).isoformat()])
    elif kind=='balances':
        w.writerow(['mode','account','order','total_bytes','remaining_bytes_at_month_end','paid_eur','refunded_eur',
                    'usage_bytes','usage_value_estimate_eur','unspent_value_estimate_eur','note'])
        for r in c.execute('SELECT * FROM package_lots WHERE created<? ORDER BY created',(end,)):
            events=c.execute('SELECT kind,bytes,cents FROM ledger_events WHERE order_reference=? AND created<?',(r['order_reference'],end)).fetchall()
            balance=sum(e['bytes'] for e in events)
            used=-sum(e['bytes'] for e in events if e['kind']=='usage')
            refunded=-sum(e['cents'] for e in events if e['kind']=='refund')
            estimate=lambda n: str((Decimal(r['cents'])*Decimal(n)/Decimal(r['total_bytes'])/100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
            w.writerow(['sandbox',r['user_id'],r['order_reference'],r['total_bytes'],balance,f"{r['cents']/100:.2f}",f"{refunded/100:.2f}",
                        used,estimate(used),estimate(balance),'Estimate only; not posted accounting revenue. SmartDNS allocation not determined.'])
    elif kind=='fees':
        w.writerow(['mode','order','intent','fee_amount','currency','status','last_observed_utc'])
        for r in c.execute('SELECT f.* FROM provider_fees f JOIN credits p ON p.order_reference=f.order_reference WHERE p.created>=? AND p.created<?',(start,end)):
            w.writerow(['sandbox',r['order_reference'],r['intent_id'],'' if r['fee_cents'] is None else f"{r['fee_cents']/100:.2f}",r['currency'],r['status'],datetime.fromtimestamp(r['observed'],timezone.utc).isoformat()])
    else: raise HTTPException(400,'invalid_export_kind')
    return ('﻿'+out.getvalue()).encode('utf-8')
