import sys,tempfile,sqlite3,json,uuid
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import tolf_billing_sandbox as sb
with tempfile.TemporaryDirectory() as td:
 d=Path(td);main=d/'main.db'
 with sqlite3.connect(main) as c:
  c.executescript("CREATE TABLE admin_roles(user_id TEXT);INSERT INTO admin_roles VALUES('admin');CREATE TABLE managed_users(number INTEGER,account_id TEXT,vpn_username TEXT,deleted_at TEXT);INSERT INTO managed_users VALUES(9,'admin','test',NULL);CREATE TABLE account_passwords(user_id TEXT,username TEXT);")
 sb.DATABASE=d/'sandbox.db';sb.CONFIG=d/'config.json';store=str(uuid.uuid4())
 sb.CONFIG.write_text(json.dumps({'environment':'sandbox','apiBase':sb.BASE,'accessKey':'test','secretKey':'x'*40,'storeUuid':store}))
 app=FastAPI();sb.install(app,{'DB':str(main),'authenticated_user_id':lambda r:'admin'})
 def fake(method,path,payload=None):
  if method=='GET':return {'uuid':store,'paymentMethods':{'cardPayments':{}}}
  return {**payload,'uuid':str(uuid.uuid4()),'paymentStatus':'PENDING','paymentUrl':'https://sandbox-stargate.montonio.com/test'}
 with patch.object(sb,'provider',side_effect=fake):
  client=TestClient(app)
  caps=client.get('/billing/capabilities').json();assert caps['pricingVersion']==sb.pricing.VERSION
  p={'package':'375','method':'cardPayments','locale':'ru','requestId':str(uuid.uuid4()),'termsVersion':sb.TERMS,'pricingVersion':sb.pricing.VERSION,'acceptTerms':True,'startNow':True}
  r=client.post('/billing/sandbox/orders',json=p,headers={'origin':sb.ORIGIN});assert r.status_code==200,r.text
  assert r.json()['amount']==19.13
  assert client.post('/billing/sandbox/orders',json={**p,'package':'49'},headers={'origin':sb.ORIGIN}).status_code==400
  assert client.post('/billing/sandbox/orders',json={**p,'pricingVersion':'old'},headers={'origin':sb.ORIGIN}).status_code==409
  print('Sandbox: custom volume, server quote, minimum and old-client rejection passed.')
