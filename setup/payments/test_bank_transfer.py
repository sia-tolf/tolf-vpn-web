import concurrent.futures
import hashlib
import json
import sqlite3
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
from fastapi import FastAPI,HTTPException
from fastapi.testclient import TestClient
import tolf_billing_live as live
import tolf_bank_transfer as bank


def test_all():
 with tempfile.TemporaryDirectory() as td:
  d=Path(td);db=d/'main.db'
  with sqlite3.connect(db) as c:
   c.executescript("CREATE TABLE admin_roles(user_id TEXT PRIMARY KEY);INSERT INTO admin_roles VALUES('admin');INSERT INTO admin_roles VALUES('other');CREATE TABLE managed_users(account_id TEXT,number INTEGER,deleted_at TEXT);INSERT INTO managed_users VALUES('admin',9,NULL);INSERT INTO managed_users VALUES('other',10,NULL);")
  app=FastAPI();live.install(app,{'DB':str(db),'authenticated_user_id':lambda r:r.headers.get('x-user','outsider')});bank.install(app,{})
  client=TestClient(app);headers={'x-user':'admin','origin':live.ORIGIN}
  payload={'package':'375','pricingVersion':bank.pricing.VERSION,'termsVersion':live.TERMS,'acceptTerms':True,'startNow':True,'locale':'ru','requestId':str(uuid.uuid4()),'buyer':{'kind':'company','name':'TEST COMPANY - Счёт для проверки','registration':'TEST12345','address':'Test address 123, Rīga','country':'LV','vatNumber':''}}
  for path in ['/billing/bank/admin/settings','/billing/bank/admin/invoices','/billing/bank/invoices']:
   assert client.get(path).status_code==403
  assert client.post('/billing/bank/invoices',json=payload).status_code==403
  assert client.get('/billing/bank/capabilities').json()['enabled'] is False
  assert client.get('/billing/bank/capabilities',headers=headers).json()['enabled'] is False
  assert client.post('/billing/bank/invoices',json=payload,headers=headers).status_code==503
  initial=client.get('/billing/bank/admin/settings',headers=headers).json();cfg={**initial['settings'],'enabled':True,'beneficiary':'TEST ONLY - NOT FOR PAYMENT','bankName':'TEST BANK','iban':'LV80BANK0000435195001','bic':'BANKLV22','vatStatus':'non_registered'}
  assert client.post('/billing/bank/admin/settings',json={'settings':{**cfg,'iban':'LV00BANK0000435195001'},'revision':1},headers=headers).status_code==400
  assert client.post('/billing/bank/admin/settings',json={'settings':cfg,'revision':1},headers={'x-user':'admin'}).status_code==403
  saved=client.post('/billing/bank/admin/settings',json={'settings':cfg,'revision':1},headers=headers);assert saved.status_code==200,saved.text
  assert client.post('/billing/bank/admin/settings',json={'settings':cfg,'revision':1},headers=headers).status_code==409
  assert client.get('/billing/bank/capabilities',headers=headers).json()['enabled'] is True
  for changes in [{'package':'49'},{'package':'1001'},{'package':'50.5'},{'pricingVersion':'old'},{'acceptTerms':False},{'buyer':None},{'cents':1}]:
   assert client.post('/billing/bank/invoices',json={**payload,**changes},headers=headers).status_code in (400,409)
  with patch.object(live,'provider',side_effect=AssertionError('Bank invoices must not call Montonio')):
   response=client.post('/billing/bank/invoices',json=payload,headers=headers);assert response.status_code==200,response.text
   invoice=response.json();assert invoice['amount']==19.13 and invoice['gb']==375 and invoice['status']=='PENDING'
   number=invoice['number'];assert number.startswith('TOLF-BT-');assert invoice['paymentReference']==number
   duplicate=client.post('/billing/bank/invoices',json=payload,headers=headers);assert duplicate.json()['number']==number
   assert client.post('/billing/bank/invoices',json={**payload,'package':'500'},headers=headers).status_code==409
   original=client.get(invoice['pdfUrl'],headers=headers);assert original.status_code==200 and original.content.startswith(b'%PDF-')
   original_hash=hashlib.sha256(original.content).hexdigest()
   assert client.get(invoice['pdfUrl'],headers={'x-user':'other'}).status_code==404
   assert client.get('/billing/bank/admin/invoices/'+number+'.pdf',headers={'x-user':'other'}).status_code==200
   assert client.get('/billing/bank/invoices/'+number+'/receipt.pdf',headers=headers).status_code==404
   with live.database() as c:
    order=c.execute('SELECT * FROM live_payment_orders WHERE reference=?',(invoice['reference'],)).fetchone()
    assert c.execute('SELECT COUNT(*) FROM live_payment_credits').fetchone()[0]==0
    try:live.match({'grandTotal':19.13},order)
    except HTTPException as e:assert e.detail=='wrong_payment_channel'
    else:raise AssertionError('Wrong channel accepted')
   received=datetime.now(ZoneInfo('Europe/Riga')).date().isoformat()
   confirm={'amount':'19.13','currency':'EUR','transactionId':'TEST-BANK-TX-0001','receivedDate':received,'confirmReceived':True}
   url='/billing/bank/admin/invoices/'+number+'/confirm'
   assert client.post(url,json=confirm).status_code==403
   for changes in [{'amount':'19.12'},{'currency':'USD'},{'confirmReceived':False},{'transactionId':''},{'receivedDate':'2999-01-01'}]:assert client.post(url,json={**confirm,**changes},headers=headers).status_code==400
   with patch.object(live,'usage',return_value=1000):
    def operation(_):return client.post(url,json=confirm,headers=headers)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
     results=list(pool.map(operation,range(2)))
    assert all(r.status_code==200 for r in results),[r.text for r in results]
   assert client.post(url,json={**confirm,'transactionId':'different'},headers=headers).status_code==409
   with live.database() as c:
    assert c.execute('SELECT COUNT(*) FROM live_payment_credits').fetchone()[0]==1
    assert c.execute('SELECT bytes FROM live_payment_credits').fetchone()[0]==375_000_000_000
    assert c.execute("SELECT COUNT(*) FROM bank_transfer_audit WHERE action='payment.confirmed'").fetchone()[0]==1
   receipt=client.get('/billing/bank/invoices/'+number+'/receipt.pdf',headers=headers);assert receipt.status_code==200 and receipt.content.startswith(b'%PDF-')
   assert hashlib.sha256(client.get(invoice['pdfUrl'],headers=headers).content).hexdigest()==original_hash
   assert client.get('/billing/bank/admin/invoices?status=PAID',headers=headers).json()['total']==1
   with patch.object(live,'usage',return_value=1000):
    account=client.get('/billing/live/account',headers=headers).json();assert account['creditedBytes']==375_000_000_000
    assert account['orders'][0]['bankInvoice']['receiptUrl']
   second=client.post('/billing/bank/invoices',json={**payload,'requestId':str(uuid.uuid4())},headers=headers).json()
   assert second['number']!=number
   assert client.post('/billing/bank/admin/invoices/'+second['number']+'/confirm',json=confirm,headers=headers).status_code==409
   with patch.object(bank,'render',side_effect=RuntimeError('Render failure')):
    try:bank.confirm(second['number'],'admin',{**confirm,'transactionId':'TX-RENDER-FAIL'})
    except RuntimeError:pass
    else:raise AssertionError('Expected failure')
   with live.database() as c:
    assert c.execute('SELECT COUNT(*) FROM live_payment_credits').fetchone()[0]==1
    assert c.execute('SELECT confirmed_at FROM bank_transfer_invoices WHERE number=?',(second['number'],)).fetchone()[0] is None
   cfg2={**cfg,'bankName':'NEW BANK','enabled':False}
   assert client.post('/billing/bank/admin/settings',json={'settings':cfg2,'revision':2},headers=headers).status_code==200
   assert client.post('/billing/bank/invoices',json={**payload,'requestId':str(uuid.uuid4())},headers=headers).status_code==503
   assert hashlib.sha256(client.get(invoice['pdfUrl'],headers=headers).content).hexdigest()==original_hash
   assert client.get('/billing/bank/invoices',headers=headers).json()['invoices'][0]['bank']['bankName']=='TEST BANK'
  # Persist only isolated preview PDFs for visual QA, never real invoices.
  preview=Path('/var/tmp/tolf-layout-qa');preview.mkdir(exist_ok=True)
  with live.database() as c:snapshot=json.loads(c.execute('SELECT snapshot FROM bank_transfer_invoices WHERE number=?',(number,)).fetchone()[0])
  for locale in ['ru','en','lv']:
   snapshot['locale']=locale;(preview/('bank-sample-'+locale+'.pdf')).write_bytes(bank.render(snapshot))
  print('PASS: bank settings, IBAN, admin gate, ownership, immutable PDFs, server prices, unique numbers, idempotent issue, atomic concurrent confirmation, transaction uniqueness, receipts, failure rollback and shared live balance.')

test_all()
