import importlib.util
import json
import sqlite3
import tempfile
import time
import uuid
from pathlib import Path
from unittest.mock import patch
import jwt
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import tolf_billing_live as live

def run():
 with tempfile.TemporaryDirectory() as td:
  d=Path(td);db=d/'users.db';cfg=d/'live.json';store=str(uuid.uuid4())
  cfg.write_text(json.dumps({'environment':'production','apiBase':live.BASE,'enabled':True,'accessKey':'live-test-key','secretKey':'x'*40,'storeUuid':store}))
  with sqlite3.connect(db) as c:
   c.executescript("CREATE TABLE admin_roles(user_id TEXT PRIMARY KEY);CREATE TABLE managed_users(account_id TEXT,deleted_at TEXT);INSERT INTO admin_roles VALUES('admin');INSERT INTO managed_users VALUES('admin',NULL);")
  app=FastAPI();live.CONFIG=cfg;live.install(app,{'DB':str(db),'authenticated_user_id':lambda r:r.headers.get('x-user','user')})
  client=TestClient(app);calls=[]
  def provider(method,path,p=None):
   calls.append((method,path))
   if path=='/stores/payment-methods':return {'uuid':store,'paymentMethods':{'cardPayments':{}}}
   return {**p,'uuid':str(uuid.uuid4()),'paymentUrl':'https://stargate.montonio.com/payment','paymentStatus':'PENDING'}
  headers={'x-user':'admin','origin':live.ORIGIN}
  p={'package':'200','method':'cardPayments','locale':'ru','requestId':str(uuid.uuid4()),'termsVersion':live.TERMS,'acceptTerms':True,'startNow':True}
  with patch.object(live,'provider',side_effect=provider),patch.object(live,'usage',return_value=123):
   for path in ['/billing/live/methods','/billing/live/account','/billing/live/orders/other']:
    assert client.get(path).status_code==403
   assert client.post('/billing/live/orders',json=p,headers={'origin':live.ORIGIN}).status_code==403
   assert calls==[]
   assert client.get('/billing/live/capabilities').json()=={'mode':'preview','enabled':False}
   assert client.get('/billing/live/capabilities',headers=headers).json()['enabled'] is True
   assert client.post('/billing/live/orders',json=p,headers={'x-user':'admin'}).status_code==403
   a=client.post('/billing/live/orders',json=p,headers=headers);assert a.status_code==200,a.text
   ref=a.json()['reference'];assert ref.startswith('TOLF-LIVE-')
   b=client.post('/billing/live/orders',json=p,headers=headers);assert b.json()['reference']==ref
   assert sum(m=='POST' for m,path in calls)==1
   assert client.post('/billing/live/orders',json={**p,'package':'50'},headers=headers).status_code==409
   with live.database() as c:row=dict(c.execute('SELECT * FROM live_payment_orders WHERE reference=?',(ref,)).fetchone())
   paid={'uuid':row['provider_uuid'],'merchantReference':ref,'currency':'EUR','grandTotal':9,'paymentStatus':'PAID','storeUuid':store}
   for field,value in [('grandTotal',1),('currency','USD'),('uuid',str(uuid.uuid4())),('storeUuid',str(uuid.uuid4()))]:
    try:live.apply_status({**paid,field:value},'test')
    except HTTPException:pass
    else:raise AssertionError(field)
   token=jwt.encode({**paid,'accessKey':'live-test-key','iat':int(time.time()),'exp':int(time.time())+120},'x'*40,algorithm='HS256')
   ret=client.post('/billing/live/validate-return',json={'orderToken':token},headers=headers);assert ret.status_code==200
   assert client.get('/billing/live/account',headers=headers).json()['creditedBytes']==0
   with patch.object(live,'provider',return_value=paid):
    for _ in range(3):assert client.post('/billing/live/notify',json={'orderToken':token}).status_code==200
   account=client.get('/billing/live/account',headers=headers).json();assert account['creditedBytes']==200_000_000_000
   with live.database() as c:assert c.execute('SELECT COUNT(*) FROM live_payment_credits').fetchone()[0]==1
   live.apply_status({**paid,'paymentStatus':'PENDING'},'test')
   assert client.get('/billing/live/account',headers=headers).json()['orders'][0]['status']=='PAID'
   with patch.object(live,'usage',return_value=1_000_000_123):assert client.get('/billing/live/account',headers=headers).json()['balanceBytes']==199_000_000_000
   assert client.post('/billing/live/notify',json={'orderToken':token+'x'}).status_code==400
   live.apply_status({**paid,'paymentStatus':'REFUNDED'},'test');live.apply_status(paid,'test')
   assert client.get('/billing/live/account',headers=headers).json()['creditedBytes']==0
   for url in ['https://sandbox-stargate.montonio.com/a','https://stargate.montonio.com.evil/a','https://x@stargate.montonio.com/a','http://stargate.montonio.com/a']:
    try:live.payment_url(url)
    except HTTPException:pass
    else:raise AssertionError(url)
   cfg.unlink();assert client.get('/billing/live/capabilities',headers=headers).json()['enabled'] is False
   assert client.post('/billing/live/orders',json=p,headers=headers).status_code==503
  print('PASS: admin gate, fail-closed config, origin, fixed prices, idempotent creation, signed return without credit, verified webhooks, duplicate credit, mismatches, usage, refunds, safe payment URLs')
run()
