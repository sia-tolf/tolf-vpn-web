import importlib.util,json,sqlite3,time,uuid,sys
from pathlib import Path
import jwt,pytest
from fastapi import FastAPI,HTTPException
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'setup/payments'))
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


def paid_order(env,**changes):
    order=create(env,**changes)
    c,state=env
    data=state['orders'][next(k for k,v in state['orders'].items() if v['merchantReference']==order['reference'])]
    assert c.post('/billing/sandbox/notify',json={'orderToken':token(data,paymentStatus='PAID')}).status_code==200
    return order,data

def test_document_is_owner_only_immutable_and_once(env):
    c,state=env;order,data=paid_order(env)
    account=c.get('/billing/sandbox/account',headers=headers()).json()
    docs=account['orders'][0]['documents']
    assert len(docs)==1
    url='/billing/sandbox/documents/'+docs[0]['number']+'.pdf'
    result=c.get(url,headers=headers())
    assert result.status_code==200 and result.content.startswith(b'%PDF-')
    assert 'attachment' in result.headers['content-disposition']
    assert c.get(url,headers=headers('other-reviewer')).status_code==404
    for _ in range(2):
        c.post('/billing/sandbox/notify',json={'orderToken':token(data,paymentStatus='PAID')})
    assert c.get(url,headers=headers()).content==result.content
    assert len(c.get('/billing/sandbox/account',headers=headers()).json()['orders'][0]['documents'])==1

def test_unpaid_order_has_no_document(env):
    order=create(env)
    c,_=env
    assert c.get('/billing/sandbox/account',headers=headers()).json()['orders'][0]['documents']==[]
    assert c.get('/billing/sandbox/documents/guessed.pdf',headers=headers()).status_code==404

@pytest.mark.parametrize('buyer',[
    {'kind':'company','name':'X','address':'Y','country':'LV'},
    {'kind':'individual','name':'','address':'Y','country':'LV'},
    {'kind':'individual','name':'X','address':'Y','country':'ZZ'},
    {'kind':'individual','name':'X','address':'Y','country':'LV','amount':1},
    {'kind':'individual','name':'X','address':'Y','country':'LV','vatNumber':'x'+chr(10)+'y'}
])
def test_invalid_billing_details_rejected(env,buyer):
    c,state=env
    assert c.post('/billing/sandbox/orders',headers=headers(),json=payload(buyer=buyer)).status_code==400
    assert state['calls']==0

def test_buyer_country_never_becomes_verified_country(env):
    c,state=env
    order,data=paid_order(env,buyer={'kind':'company','name':'=FORMULA','address':'Rīga <test>','country':'LV','registration':'123'})
    account=c.get('/billing/sandbox/account',headers=headers()).json()['orders'][0]
    info=account['countryEvidence']
    assert info['country'] is None and info['status']=='unresolved'
    assert info['evidence'][0]['provenance']=='merchant_or_customer_declared'
    month=time.strftime('%Y-%m',time.gmtime())
    export=c.get('/billing/sandbox/admin/export.csv?month='+month,headers=headers('admin'))
    assert export.status_code==200 and "'=FORMULA" in export.text
    assert c.get('/billing/sandbox/admin/export.csv?month='+month,headers=headers()).status_code==403

def test_gateway_country_and_merchant_iban_not_payer_evidence(env):
    c,state=env;order,data=paid_order(env,method='paymentInitiation',bankCountry='LV',bankCode='TESTBANK')
    data['paymentStatus']='PAID'
    data['paymentIntents']=[{'uuid':str(uuid.uuid4()),'paymentMethodMetadata':{'preferredCountry':'LV','receiverIban':'LV80HABA1234567890123','preferredProvider':'HABALV22'},'paymentMetadata':{'cardPaymentPricingGroup':'EU_CONSUMER'},'status':'PAID','serviceFee':None,'serviceFeeCurrency':'EUR'}]
    sb.apply_status(data,'api')
    info=c.get('/billing/sandbox/account',headers=headers()).json()['orders'][0]['countryEvidence']
    assert info['country'] is None
    assert info['evidence']==[{'field':'paymentMethodMetadata.preferredCountry','country':'LV','provenance':'gateway_selection_not_tax_evidence'}]

def test_fifo_usage_idempotency_and_balance(env):
    c,state=env
    first,_=paid_order(env,package='50')
    second,_=paid_order(env,package='200')
    p={'userId':'reviewer','eventId':'usage-test-001','bytes':75_000_000_000}
    for _ in range(2):
        assert c.post('/billing/sandbox/admin/usage',headers=headers('admin'),json=p).status_code==200
    account=c.get('/billing/sandbox/account',headers=headers()).json()
    assert account['testBalanceBytes']==175_000_000_000
    remaining={o['reference']:o['remainingBytes'] for o in account['orders']}
    assert remaining[first['reference']]==0 and remaining[second['reference']]==175_000_000_000
    assert c.post('/billing/sandbox/admin/usage',headers=headers(),json=p).status_code==403
    assert c.post('/billing/sandbox/admin/usage',headers=headers('admin'),json={**p,'bytes':1}).status_code==409
    assert c.post('/billing/sandbox/admin/usage',headers=headers('admin'),json={**p,'eventId':'usage-test-002','bytes':10**12}).status_code==409

def test_verified_refund_corrects_without_duplicate_or_negative_balance(env):
    c,state=env;order,data=paid_order(env)
    data['paymentStatus']='REFUNDED'
    data['refunds']=[{'uuid':str(uuid.uuid4()),'status':'SUCCESSFUL','currency':'EUR','amount':'9.00'}]
    sb.apply_status(data,'api');sb.apply_status(data,'api')
    account=c.get('/billing/sandbox/account',headers=headers()).json()
    assert account['testBalanceBytes']==0
    assert len(account['orders'][0]['documents'])==2
    assert account['orders'][0]['status']=='REFUNDED'
    c.post('/billing/sandbox/notify',json={'orderToken':token(data,paymentStatus='PENDING')})
    assert c.get('/billing/sandbox/account',headers=headers()).json()['orders'][0]['status']=='REFUNDED'
    with sb.database() as db:
        assert db.execute("SELECT COUNT(*) FROM ledger_events WHERE kind='refund'").fetchone()[0]==1
        assert db.execute('SELECT SUM(cents) FROM ledger_events').fetchone()[0]==0

def test_month_export_and_fee_unknown_distinct_from_zero(env):
    c,state=env;order,data=paid_order(env)
    data['paymentStatus']='PAID'
    data['paymentIntents']=[{'uuid':str(uuid.uuid4()),'status':'PAID','serviceFee':None,'serviceFeeCurrency':'EUR'}]
    sb.apply_status(data,'api')
    month=time.strftime('%Y-%m',time.gmtime())
    for kind in ['purchases','movements','balances','fees']:
        result=c.get('/billing/sandbox/admin/export.csv?month='+month+'&kind='+kind,headers=headers('admin'))
        assert result.status_code==200 and result.content.startswith(bytes.fromhex('efbbbf'))
        assert order['reference'] in result.text
    assert ',,EUR,' in result.text
    assert c.get('/billing/sandbox/admin/export.csv?month=2026-13',headers=headers('admin')).status_code==400
    assert c.get('/billing/sandbox/admin/export.csv?month='+month+'&kind=bad',headers=headers('admin')).status_code==400
