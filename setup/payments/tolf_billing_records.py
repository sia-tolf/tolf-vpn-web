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
    CREATE TABLE IF NOT EXISTS order_identity(
        order_reference TEXT PRIMARY KEY, account_label TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS document_presentations(
        number TEXT PRIMARY KEY, account_label TEXT NOT NULL, pdf BLOB NOT NULL, created REAL NOT NULL);
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
    story+=block(x['buyer'],[b.get('name',snapshot.get('accountLabel') or x['account']),b.get('registration'),b.get('vatNumber'),b.get('address'),b.get('country')])
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
        related={'ru':'Первоначальный документ','en':'Original document','lv':'Sākotnējais dokuments'}[snapshot['locale']]
        story += [Spacer(1,12),para(related+': '+snapshot['originalDocument'],muted)]
    if snapshot.get('paymentCreated'):
        paid_label={'ru':'Дата оплаты (UTC)','en':'Payment date (UTC)','lv':'Apmaksas datums (UTC)'}[snapshot['locale']]
        story += [para(paid_label+': '+datetime.fromtimestamp(snapshot['paymentCreated'],timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),muted)]
    doc.build(story)
    return output.getvalue()

def create_document(c,row,kind='purchase',external_id=None,cents=None,buyer_override=None):
    existing=c.execute('SELECT number FROM documents WHERE order_reference=? AND kind=? AND external_id IS ?',
                       (row['reference'],kind,external_id)).fetchone()
    if existing: return existing[0]
    now=time.time()
    year=datetime.fromtimestamp(now,timezone.utc).year
    prefix='TOLF-SB-'+('CR-' if kind=='refund' else '')+str(year)+'-'
    seq=c.execute('SELECT COUNT(*)+1 FROM documents WHERE number LIKE ?',(prefix+'%',)).fetchone()[0]
    number=prefix+str(seq).zfill(6)
    details=c.execute('SELECT buyer_json FROM checkout_details WHERE order_reference=?',(row['reference'],)).fetchone()
    buyer=buyer_override if buyer_override is not None else json.loads(details[0]) if details else {}
    paid=c.execute('SELECT created FROM credits WHERE order_reference=?',(row['reference'],)).fetchone()
    original=c.execute("SELECT number FROM documents WHERE order_reference=? AND kind='purchase'",(row['reference'],)).fetchone()
    identity=c.execute('SELECT account_label FROM order_identity WHERE order_reference=?',(row['reference'],)).fetchone()
    snapshot={'version':1,'number':number,'kind':kind,'created':paid[0] if kind=='purchase' and paid else now,
              'issuedAt':now,'locale':'lv' if buyer.get('country')=='LV' else 'en','seller':dict(SELLER),'buyer':buyer,
              'accountReference':row['user_id'],'accountLabel':identity[0] if identity else None,'orderReference':row['reference'],'gb':row['gb'],
              'cents':row['cents'] if cents is None else cents,'currency':'EUR','taxPolicy':POLICY,
              'taxCountry':None,'vatRate':None,'vatCents':None,'environment':'sandbox',
              'originalDocument':original[0] if kind in {'refund','billing_details'} and original else None}
    if kind=='billing_details':
        original_snapshot=json.loads(c.execute("SELECT snapshot_json FROM documents WHERE number=?",(original[0],)).fetchone()[0])
        for key in ['seller','taxPolicy','taxCountry','vatRate','vatCents','cents','currency','gb','environment']:
            snapshot[key]=original_snapshot[key]
        snapshot['paymentCreated']=original_snapshot['created']
    encoded=json.dumps(snapshot,ensure_ascii=False,sort_keys=True)
    c.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?)',(number,row['reference'],kind,external_id,encoded,render_pdf(snapshot),now))
    return number

def document_pdf(c,number):
    document=c.execute('SELECT snapshot_json,pdf,order_reference FROM documents WHERE number=?',(number,)).fetchone()
    if not document:
        return None
    presentation=c.execute('SELECT pdf FROM document_presentations WHERE number=?',(number,)).fetchone()
    if presentation:
        return bytes(presentation[0])
    snapshot=json.loads(document['snapshot_json'])
    if snapshot['buyer'] or snapshot.get('accountLabel'):
        return bytes(document['pdf'])
    identity=c.execute('SELECT account_label FROM order_identity WHERE order_reference=?',(document['order_reference'],)).fetchone()
    # Only the technical account caption is corrected. The originally issued PDF and
    # financial snapshot remain in documents, unchanged, for audit.
    snapshot['accountLabel']=identity[0] if identity else None
    rendered=render_pdf(snapshot)
    c.execute('INSERT OR IGNORE INTO document_presentations VALUES(?,?,?,?)',
              (number,snapshot['accountLabel'] or '',rendered,time.time()))
    return bytes(c.execute('SELECT pdf FROM document_presentations WHERE number=?',(number,)).fetchone()[0])

def request_billing_document(c,row,buyer):
    if row['status'] not in {'PAID','PARTIALLY_REFUNDED','REFUNDED'}:
        raise HTTPException(409,'paid_order_required')
    if not buyer:
        raise HTTPException(400,'buyer_details_required')
    original=c.execute("SELECT number,snapshot_json FROM documents WHERE order_reference=? AND kind='purchase'",(row['reference'],)).fetchone()
    if not original:
        raise HTTPException(409,'purchase_document_not_ready')
    existing=c.execute("SELECT number,snapshot_json FROM documents WHERE order_reference=? AND kind='billing_details'",(row['reference'],)).fetchone()
    if not existing and json.loads(original['snapshot_json'])['buyer']:
        existing=original
    if existing:
        if json.loads(existing['snapshot_json'])['buyer']!=buyer:
            raise HTTPException(409,'billing_document_already_issued')
        return existing['number']
    return create_document(c,row,'billing_details','billing-details:'+row['reference'],buyer_override=buyer)

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
    billing=c.execute("SELECT number FROM documents WHERE order_reference=? AND kind='billing_details'",(ref,)).fetchone()
    if not billing:
        original=c.execute("SELECT number,snapshot_json FROM documents WHERE order_reference=? AND kind='purchase'",(ref,)).fetchone()
        if original and json.loads(original['snapshot_json'])['buyer']:
            billing=original
    result['billingDocumentNumber']=billing['number'] if billing else None
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
        for r in c.execute("SELECT * FROM documents WHERE created>=? AND created<? AND kind!='billing_details' ORDER BY created",(start,end)):
            d=json.loads(r['snapshot_json'])
            supplement=c.execute("SELECT snapshot_json FROM documents WHERE order_reference=? AND kind='billing_details'",(r['order_reference'],)).fetchone()
            if supplement:
                d['buyer']=json.loads(supplement[0])['buyer']
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

EXPORT_TEXT = {
 'ru': {'title':'Бухгалтерская выгрузка TOLF','test':'ТЕСТОВЫЕ ДАННЫЕ - SANDBOX',
        'period':'Период (UTC)','generated':'Сформировано (UTC)','rows':'Количество записей','empty':'За выбранный период записей нет.',
        'purchases':'Покупки и возвраты','movements':'Движение трафика','balances':'Остатки пакетов','fees':'Комиссии Montonio',
        'note':'Реальные деньги не списывались. Это тестовый отчёт, а не налоговый счёт. Пустое значение обозначено прочерком.',
        'balanceNote':'Остатки рассчитаны на конец выбранного месяца; для текущего месяца - по имеющимся данным. Оценки стоимости не являются бухгалтерскими проводками. Распределение стоимости SmartDNS не определено.',
        'feeNote':'Отсутствующая комиссия не считается нулевой. Показаны последние известные сведения по оплатам выбранного месяца.',
        'page':'Страница','total':'Итого','refunds':'Возвраты','sales':'Покупки','knownFees':'Известные комиссии','unknownFees':'Комиссия неизвестна'},
 'en': {'title':'TOLF accounting export','test':'TEST DATA - SANDBOX',
        'period':'Period (UTC)','generated':'Generated (UTC)','rows':'Record count','empty':'No records for the selected period.',
        'purchases':'Purchases and refunds','movements':'Traffic movements','balances':'Package balances','fees':'Montonio fees',
        'note':'No real money was charged. This is a test report, not a VAT invoice. A dash indicates an unavailable value.',
        'balanceNote':'Balances are calculated at month end; the current month uses available data. Value estimates are not accounting entries. SmartDNS allocation is not determined.',
        'feeNote':'An unavailable fee is not zero. Latest known information is shown for payments made in the selected month.',
        'page':'Page','total':'Total','refunds':'Refunds','sales':'Purchases','knownFees':'Known fees','unknownFees':'Unknown fee'},
 'lv': {'title':'TOLF grāmatvedības eksports','test':'TESTA DATI - SANDBOX',
        'period':'Periods (UTC)','generated':'Sagatavots (UTC)','rows':'Ierakstu skaits','empty':'Izvēlētajā periodā ierakstu nav.',
        'purchases':'Pirkumi un atmaksas','movements':'Datu kustība','balances':'Paku atlikumi','fees':'Montonio komisijas',
        'note':'Reāla nauda netika iekasēta. Šis ir testa pārskats, nevis PVN rēķins. Trūkstošā vērtība apzīmēta ar svītru.',
        'balanceNote':'Atlikumi aprēķināti mēneša beigās; tekošajam mēnesim izmantoti pieejamie dati. Vērtības aplēses nav grāmatvedības ieraksti. SmartDNS vērtības sadalījums nav noteikts.',
        'feeNote':'Nezināma komisija nav nulle. Norādīta jaunākā zināmā informācija par izvēlētā mēneša maksājumiem.',
        'page':'Lapa','total':'Kopā','refunds':'Atmaksas','sales':'Pirkumi','knownFees':'Zināmās komisijas','unknownFees':'Nezināma komisija'}
}
EXPORT_FIELDS = {
 'document':('Документ','Document','Dokuments'),
 'issued_utc':('Дата документа (UTC)','Document date (UTC)','Dokumenta datums (UTC)'),
 'paid_utc':('Дата операции (UTC)','Transaction date (UTC)','Darījuma datums (UTC)'),
 'order':('Заказ','Order','Pasūtījums'),
 'buyer_name':('Покупатель','Buyer','Pircējs'),
 'buyer_registration':('Регистрационный номер','Registration number','Reģistrācijas numurs'),
 'gb':('Объём, ГБ','Volume, GB','Apjoms, GB'),
 'gross_eur':('Сумма, EUR','Amount, EUR','Summa, EUR'),
 'vat_policy':('Налоговая политика','Tax policy','Nodokļu politika'),
 'tax_country':('Страна для налогов','Tax country','Nodokļu valsts'),
 'country_status':('Статус страны','Country status','Valsts statuss'),
 'event':('Идентификатор события','Event ID','Notikuma ID'),
 'account':('Идентификатор аккаунта','Account ID','Konta ID'),
 'kind':('Тип операции','Movement type','Darījuma veids'),
 'bytes':('Изменение трафика','Traffic change','Datu izmaiņa'),
 'eur':('Изменение суммы, EUR','Amount change, EUR','Summas izmaiņa, EUR'),
 'utc':('Дата (UTC)','Date (UTC)','Datums (UTC)'),
 'total_bytes':('Начисленный объём','Credited traffic','Ieskaitītie dati'),
 'remaining_bytes_at_month_end':('Остаток на конец месяца','Month-end traffic balance','Datu atlikums mēneša beigās'),
 'paid_eur':('Оплачено, EUR','Paid, EUR','Samaksāts, EUR'),
 'refunded_eur':('Возвращено, EUR','Refunded, EUR','Atmaksāts, EUR'),
 'usage_bytes':('Использованный объём','Used traffic','Izmantotie dati'),
 'usage_value_estimate_eur':('Оценка стоимости расхода, EUR','Estimated usage value, EUR','Izlietojuma vērtības aplēse, EUR'),
 'unspent_value_estimate_eur':('Оценка стоимости остатка, EUR','Estimated remaining value, EUR','Atlikuma vērtības aplēse, EUR'),
 'note':('Примечание','Note','Piezīme'),
 'intent':('Идентификатор платежа','Payment intent ID','Maksājuma ID'),
 'fee_amount':('Комиссия','Fee','Komisija'),
 'currency':('Валюта','Currency','Valūta'),
 'status':('Статус','Status','Statuss'),
 'last_observed_utc':('Последнее обновление (UTC)','Last observed (UTC)','Pēdējais novērojums (UTC)')
}

def export_pdf(c,month,kind,locale='en'):
    if locale not in EXPORT_TEXT:
        raise HTTPException(400,'invalid_locale')
    # Reuse the CSV snapshot so both formats have the same filtering and data.
    raw=export(c,month,kind).decode('utf-8-sig')
    reader=csv.DictReader(io.StringIO(raw))
    fields=list(reader.fieldnames)
    rows=list(reader)
    x=EXPORT_TEXT[locale]
    lang_index={'ru':0,'en':1,'lv':2}[locale]
    now=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    output=io.BytesIO()
    doc=SimpleDocTemplate(output,pagesize=(595.28,841.89),leftMargin=36,rightMargin=36,topMargin=36,bottomMargin=42,
                          title=x['title']+' - '+month+' - '+x[kind],author='SIA Tolf')
    normal=ParagraphStyle('report',fontName='Tolf',fontSize=9,leading=13,textColor=colors.HexColor('#202124'),wordWrap='CJK')
    bold=ParagraphStyle('reportBold',parent=normal,fontName='TolfBold')
    muted=ParagraphStyle('reportMuted',parent=normal,fontSize=8,leading=12,textColor=colors.HexColor('#666666'))
    title=ParagraphStyle('reportTitle',parent=bold,fontSize=19,leading=25,spaceAfter=8)
    def para(value,style=normal):return Paragraph(escape(str(value)),style)
    story=[para(x['title'],title),para(x[kind],ParagraphStyle('reportSubtitle',parent=bold,fontSize=13,leading=18)),
           Spacer(1,10),para(x['test'],bold),para(SELLER['name']+' | '+SELLER['registration']),
           para(x['period']+': '+month+' | '+x['rows']+': '+str(len(rows))),para(x['generated']+': '+now,muted),
           Spacer(1,10),para(x['note'],muted)]
    if kind in ('balances','fees'):
        story.append(para(x['balanceNote' if kind=='balances' else 'feeNote'],muted))
    if kind=='purchases':
        sales=sum((Decimal(row['gross_eur']) for row in rows if not row['document'].startswith('TOLF-SB-CR-')),Decimal(0))
        refunds=sum((Decimal(row['gross_eur']) for row in rows if row['document'].startswith('TOLF-SB-CR-')),Decimal(0))
        story += [Spacer(1,10),para(x['sales']+': '+f'{sales:.2f} EUR'+' | '+x['refunds']+': '+f'{refunds:.2f} EUR'+' | '+x['total']+': '+f'{sales-refunds:.2f} EUR',bold)]
    elif kind=='fees':
        known={}
        for row in rows:
            if row['fee_amount'] and row['currency']:
                known[row['currency']]=known.get(row['currency'],Decimal(0))+Decimal(row['fee_amount'])
        unknown=sum(1 for row in rows if not row['fee_amount'] or not row['currency'])
        story += [Spacer(1,10),para(x['knownFees']+': '+(' / '.join(f'{v:.2f} {k}' for k,v in sorted(known.items())) or '-')+' | '+x['unknownFees']+': '+str(unknown),bold)]
    story.append(Spacer(1,14))
    if not rows:
        story.append(para(x['empty']))
    for index,row in enumerate(rows,1):
        heading=str(index)+'. '+(row.get('document') or row.get('event') or row.get('order') or '')
        if kind=='purchases' and row['document'].startswith('TOLF-SB-CR-'):
            heading=x['refunds']+' - '+heading
        record=[ [para(heading,bold),para('')] ]
        for key in fields:
            if key=='mode':
                continue
            value=row[key] or '-'
            if key in ('bytes','total_bytes','remaining_bytes_at_month_end','usage_bytes'):
                value=f"{Decimal(value)/Decimal(1000000000):.3f} GB ({value} B)"
            elif key in ('issued_utc','paid_utc','utc','last_observed_utc') and value!='-':
                value=datetime.fromisoformat(value).astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            elif key=='note' and kind=='balances':
                value=x['balanceNote']
            elif key=='country_status' and value=='unresolved':
                value={'ru':'Не определена','en':'Unresolved','lv':'Nav noteikta'}[locale]
            elif key=='kind':
                value={'purchase':{'ru':'Начисление','en':'Purchase credit','lv':'Ieskaitīšana'},
                       'usage':{'ru':'Расход','en':'Usage','lv':'Izlietojums'},
                       'refund':{'ru':'Возврат','en':'Refund','lv':'Atmaksa'}}.get(value,{}).get(locale,value)
            record.append([para(EXPORT_FIELDS[key][lang_index],muted),para(value)])
        table=Table(record,colWidths=[172,351.28],repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([
            ('SPAN',(0,0),(-1,0)),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf0f8')),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f7f8fa')]),
            ('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),
            ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        story += [table,Spacer(1,14)]
    def footer(canvas,document):
        canvas.saveState()
        canvas.setFont('Tolf',8);canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawString(36,23,'TOLF | SANDBOX | '+month)
        canvas.drawRightString(559.28,23,x['page']+' '+str(document.page))
        canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
