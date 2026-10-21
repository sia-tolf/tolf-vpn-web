import importlib.util,json,sqlite3,time,uuid
from pathlib import Path
import jwt,pytest
from fastapi import FastAPI,HTTPException
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('sandbox',ROOT/'setup/payments/tolf_billing_sandbox.py')
sb=importlib.util.module_from_spec(spec);spec.loader.exec_module(sb)
KEY='sandbox-test-key-for-tests-only-32-characters'
@pytest.fixture
def env(tmp_path,monkeypatch):
    sb.CONFIG=tmp_path/'config.json';sb.DATABASE=tmp_path/'sandbox.db'
    sb.CONFIG.write_text(json.dumps({'environment':'sandbox','apiBase':sb.BASE,'accessKey':'access-test','secretKey':KEY,'storeUuid':'store-test','reviewerIds':['reviewer','other-reviewer']}))
    main=tmp_path/'main.db'
    with sqlite3.connect(main) as c:
        c.execute('CREATE TABLE admin_roles(user_id TEXT PRIMARY KEY)')
        c.execute("INSERT INTO admin_roles VALUES ('admin')")
    state={'calls':0,'orders':{}}
    def provider(method,path,p=None):
        if path=='/stores/payment-methods':
            return {'uuid':'store-test','paymentMethods':{'cardPayments':{},'paymentInitiation':{'setup':{'LV':{'paymentMethods':[{'code':'TESTBANK','name':'Test Bank','supportedCurrencies':['EUR']}]}}}}}
        if method=='POST':
            state['calls']+=1
            data={**p,'uuid':str(uuid.uuid4()),'storeUuid':'store-test','paymentStatus':'PENDING','paymentUrl':'https://sandbox-stargate.montonio.com/test'}
            state['orders'][data['uuid']]=data
            return data
        return state['orders'][path.rsplit('/',1)[-1]]
    monkeypatch.setattr(sb,'provider',provider)
    def auth(request):
        uid=request.headers.get('x-user')
        if not uid:raise HTTPException(401,'not_authenticated')
        return uid
    app=FastAPI();sb.install(app,{'DB':str(main),'authenticated_user_id':auth})
    with TestClient(app) as client:
        yield client,state

def headers(user='reviewer'):
    return {'x-user':user,'origin':sb.ORIGIN}
def payload(**changes):
    return {'package':'200','method':'cardPayments','locale':'en','requestId':str(uuid.uuid4()),'termsVersion':sb.TERMS,'acceptTerms':True,'startNow':True,**changes}
def token(data,**changes):
    return jwt.encode({**data,'accessKey':'access-test','iat':int(time.time()),'exp':int(time.time())+300,**changes},KEY,algorithm='HS256')
def create(env,**changes):
    c,state=env;r=c.post('/billing/sandbox/orders',headers=headers(),json=payload(**changes));assert r.status_code==200,r.text
    return r.json()

def test_access_is_restricted(env):
    c,_=env
    assert c.get('/billing/capabilities').json()['enabled'] is False
    assert c.get('/billing/capabilities',headers=headers('ordinary')).json()['enabled'] is False
    assert c.get('/billing/sandbox/account',headers=headers('ordinary')).status_code==403
    assert c.get('/billing/capabilities',headers=headers('admin')).json()['mode']=='sandbox'
    assert c.get('/billing/sandbox/account',headers=headers()).json()['testBalanceBytes']==0

@pytest.mark.parametrize('changes',[{'amount':0.01},{'userId':'victim'},{'acceptTerms':False},{'startNow':False},{'termsVersion':'old'},{'package':'1'},{'package':[]},{'locale':[]},{'method':'applePay'},{'method':'paymentInitiation','bankCountry':'LV','bankCode':'forged'}])
def test_tampering_and_consent_rejected(env,changes):
    c,state=env
    assert c.post('/billing/sandbox/orders',headers=headers(),json=payload(**changes)).status_code==400
    assert state['calls']==0

def test_origin_and_body_limits(env):
    c,_=env
    assert c.post('/billing/sandbox/orders',headers={'x-user':'reviewer'},json=payload()).status_code==403
    assert c.post('/billing/sandbox/orders',headers={**headers(),'content-type':'application/json'},content='x'*16001).status_code==413

def test_idempotent_creation_and_authoritative_price(env):
    c,state=env;p=payload()
    first=c.post('/billing/sandbox/orders',headers=headers(),json=p)
    second=c.post('/billing/sandbox/orders',headers=headers(),json=p)
    assert first.json()==second.json();assert state['calls']==1
    assert first.json()['amount']==9 and first.json()['gb']==200
    assert c.get('/billing/sandbox/orders/'+first.json()['reference'],headers=headers('other-reviewer')).status_code==404

def test_verified_webhook_is_idempotent_and_paid_is_monotonic(env):
    c,state=env;order=create(env);data=next(iter(state['orders'].values()))
    t=token(data,paymentStatus='PAID')
    for _ in range(3):
        assert c.post('/billing/sandbox/notify',json={'orderToken':t}).status_code==200
    assert c.get('/billing/sandbox/account',headers=headers()).json()['testBalanceBytes']==200_000_000_000
    assert c.post('/billing/sandbox/notify',json={'orderToken':token(data,paymentStatus='PENDING')}).status_code==200
    assert c.get('/billing/sandbox/account',headers=headers()).json()['orders'][0]['status']=='PAID'
    with sqlite3.connect(sb.DATABASE) as con:assert con.execute('select count(*) from credits').fetchone()[0]==1

@pytest.mark.parametrize('changes',[{'grandTotal':0.01},{'currency':'USD'},{'accessKey':'other'},{'uuid':str(uuid.uuid4())},{'storeUuid':'other'},{'exp':1}])
def test_mismatched_notifications_do_not_credit(env,changes):
    c,state=env;create(env);data=next(iter(state['orders'].values()))
    assert c.post('/billing/sandbox/notify',json={'orderToken':token(data,paymentStatus='PAID',**changes)}).status_code==400
    assert c.get('/billing/sandbox/account',headers=headers()).json()['testBalanceBytes']==0

def test_invalid_signature_and_algorithms(env):
    c,state=env;create(env);data=next(iter(state['orders'].values()))
    t=jwt.encode({**data,'accessKey':'access-test','iat':int(time.time()),'exp':int(time.time())+100,'paymentStatus':'PAID'},'other-key-should-not-work-32-characters',algorithm='HS256')
    assert c.post('/billing/sandbox/notify',json={'orderToken':t}).status_code==400
    assert c.get('/billing/sandbox/account',headers=headers()).json()['testBalanceBytes']==0

def test_return_alone_never_credits_and_wrong_owner_denied(env):
    c,state=env;order=create(env);data=next(iter(state['orders'].values()))
    t=token(data,paymentStatus='PAID')
    assert c.post('/billing/sandbox/validate-return',headers=headers('other-reviewer'),json={'orderToken':t}).status_code==404
    assert c.post('/billing/sandbox/validate-return',headers=headers(),json={'orderToken':t}).status_code==200
    assert c.get('/billing/sandbox/account',headers=headers()).json()['testBalanceBytes']==0
    state['orders'][data['uuid']]['paymentStatus']='PAID'
    assert c.get('/billing/sandbox/orders/'+order['reference'],headers=headers()).json()['status']=='PAID'
    assert c.get('/billing/sandbox/account',headers=headers()).json()['testBalanceBytes']==200_000_000_000

def test_unsafe_redirect_never_returned(env,monkeypatch):
    c,state=env;original=sb.provider
    def bad(method,path,p=None):
        d=original(method,path,p)
        if method=='POST':d['paymentUrl']='https://stargate.montonio.com/live-order'
        return d
    monkeypatch.setattr(sb,'provider',bad)
    assert c.post('/billing/sandbox/orders',headers=headers(),json=payload()).status_code==502
    assert c.get('/billing/sandbox/account',headers=headers()).json()['testBalanceBytes']==0

def test_config_rejects_live_mode(env):
    c,state=env
    data=json.loads(sb.CONFIG.read_text());data['environment']='live';sb.CONFIG.write_text(json.dumps(data))
    assert c.get('/billing/capabilities',headers=headers()).json()['enabled'] is False
    assert c.get('/billing/sandbox/account',headers=headers()).status_code==503
