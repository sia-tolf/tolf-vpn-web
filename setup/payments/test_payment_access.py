"""Isolated payment grants: no production credentials or provider requests."""
import json,sqlite3,tempfile,uuid
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI,HTTPException
from fastapi.testclient import TestClient
import tolf_billing_live as live

def run():
 with tempfile.TemporaryDirectory() as td:
  db=Path(td)/'test.db';cfg=Path(td)/'live.json'
  cfg.write_text(json.dumps({'environment':'production','apiBase':live.BASE,'enabled':True,'accessKey':'test','secretKey':'x'*40,'storeUuid':str(uuid.uuid4())}))
  with sqlite3.connect(db) as c:
   c.executescript("CREATE TABLE admin_roles(user_id TEXT PRIMARY KEY);CREATE TABLE managed_users(account_id TEXT,deleted_at TEXT);INSERT INTO admin_roles VALUES('ipad');INSERT INTO managed_users VALUES('ipad',NULL),('user0',NULL),('other',NULL),('deleted','deleted');")
  live.CONFIG=cfg;app=FastAPI();live.install(app,{'DB':str(db),'authenticated_user_id':lambda r:r.headers.get('x-user','other')})
  client=TestClient(app)
  with live.database() as c:
   c.execute("INSERT INTO live_payment_access VALUES('user0',1,'test')")
   c.execute("INSERT INTO live_payment_access VALUES('deleted',1,'test')")
  with patch.object(live,'methods',return_value={'methods':['cardPayments']}),patch.object(live,'provider',side_effect=AssertionError('No real provider request')):
   for uid in ['user0','ipad']:
    h={'x-user':uid}
    assert client.get('/billing/live/capabilities',headers=h).json()['enabled']
    assert client.get('/billing/live/methods',headers=h).status_code==200
    assert client.get('/billing/live/account',headers=h).status_code==200
    assert client.get('/billing/live/orders/not-owned',headers=h).status_code==404
   for uid in ['other','deleted']:
    h={'x-user':uid}
    assert client.get('/billing/live/capabilities',headers=h).json()['enabled'] is False
    for path in ['/billing/live/methods','/billing/live/account','/billing/live/orders/unknown']:
     assert client.get(path,headers=h).status_code==403
    assert client.post('/billing/live/orders',headers=h,json={}).status_code==403
   class R:headers={'x-user':'user0'}
   try:live.admin(R())
   except HTTPException as e:assert e.status_code==403
   else:raise AssertionError('Payment grant must not grant administration')
   payload={'package':'50','method':'cardPayments','locale':'ru','requestId':str(uuid.uuid4()),'termsVersion':live.TERMS,'pricingVersion':live.pricing.VERSION,'acceptTerms':True,'startNow':True}
   with patch.object(live,'create',return_value={'reference':'mock-only'}) as create:
    assert client.post('/billing/live/orders',headers={'x-user':'user0','origin':live.ORIGIN},json=payload).status_code==200
    assert create.call_args.args[0]=='user0'
   with live.database() as c:c.execute("DELETE FROM live_payment_access WHERE user_id='user0'")
   assert client.get('/billing/live/account',headers={'x-user':'user0'}).status_code==403
   assert client.get('/billing/live/account',headers={'x-user':'ipad'}).status_code==200
  print('PASS: explicit payment access, existing administrator retained, denied unrelated/deleted accounts, owner checks, checkout gate, revocation, no administration granted, no real orders.')
if __name__=='__main__':run()
