import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
import uuid
from contextlib import closing, nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI,HTTPException,Request

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'setup/trials'))
import tolf_trial_packages as module
import tolf_trial_access as native
from billing_wallet_patch import patch as patch_billing


class WalletTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=str(Path(self.temp.name)/'db')
        self.uid,self.other,self.admin=[str(uuid.uuid4()) for _ in range(3)];self.counters={self.uid:123000000,self.other:0,self.admin:999}
        with closing(sqlite3.connect(self.path)) as c,c:
            c.executescript('''
            CREATE TABLE users(id TEXT PRIMARY KEY);
            CREATE TABLE admin_roles(user_id TEXT);CREATE TABLE vpn_imports(user_id TEXT,protected INTEGER);
            CREATE TABLE managed_users(account_id TEXT,source TEXT,deleted_at TEXT);
            CREATE TABLE live_payment_credits(reference TEXT PRIMARY KEY,user_id TEXT,bytes INTEGER,created REAL);
            CREATE TABLE live_payment_usage_baselines(user_id TEXT PRIMARY KEY,usage_bytes INTEGER,created REAL);
            CREATE TABLE account_trial_registrations(user_id TEXT PRIMARY KEY,registered_at TEXT,source TEXT);
            CREATE TABLE vpn_access(user_id TEXT,vpn_username TEXT);
            CREATE TABLE windows_devices(id TEXT,user_id TEXT,username TEXT,state TEXT);
            CREATE TABLE oc_devices(user_id TEXT,username TEXT,state TEXT);
            CREATE TABLE ike_mobile_us(user_id TEXT,state TEXT);
            ''')
            for uid in [self.uid,self.other,self.admin]:
                c.execute('INSERT INTO users VALUES(?)',(uid,));c.execute('INSERT INTO managed_users VALUES(?,?,NULL)',(uid,'site'))
            c.execute('INSERT INTO admin_roles VALUES(?)',(self.admin,))
        self.a=module.Trials({'DB':self.path},usage=lambda c,uid:self.counters[uid])

    def tearDown(self):self.temp.cleanup()

    def test_once_per_account_and_only_post_grant_usage(self):
        with self.a.db() as c:
            initial=self.a.claim(c,self.uid);self.assertEqual(initial['balanceBytes'],1000000000)
            self.counters[self.uid]+=250000000
            balance=self.a.balance(c,self.uid,self.counters[self.uid]);self.assertEqual(balance['balanceBytes'],750000000)
            repeated=self.a.claim(c,self.uid);self.assertEqual(repeated['balanceBytes'],750000000)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM trial_traffic_packages').fetchone()[0],1)
            self.assertIsNone(self.a.balance(c,self.other))
            self.assertEqual(c.execute('SELECT COUNT(*) FROM live_payment_credits').fetchone()[0],0)

    def test_trial_first_then_paid_without_double_charge(self):
        with self.a.db() as c:
            self.a.claim(c,self.uid);self.counters[self.uid]+=400000000
            self.a.balance(c,self.uid,self.counters[self.uid])
            c.execute('INSERT INTO live_payment_credits VALUES(?,?,?,0)',('paid',self.uid,50000000000))
            self.counters[self.uid]+=300000000
            p=self.a.balance(c,self.uid,self.counters[self.uid]);self.assertEqual(p['balanceBytes'],300000000);self.assertEqual(p['paidUsedBytes'],0)
            self.counters[self.uid]+=500000000
            p=self.a.balance(c,self.uid,self.counters[self.uid]);self.assertEqual(p['balanceBytes'],0);self.assertEqual(p['paidUsedBytes'],200000000);self.assertEqual(p['paidBalanceBytes'],49800000000)

    def test_exhaustion_counter_drop_and_unfunded_overrun(self):
        with self.a.db() as c:
            self.a.claim(c,self.uid);self.counters[self.uid]+=1500000000
            p=self.a.balance(c,self.uid,self.counters[self.uid]);self.assertEqual(p['balanceBytes'],0);self.assertEqual(p['unfundedBytes'],500000000)
            self.assertEqual(p['state'],'exhausted')
            lower=self.a.balance(c,self.uid,0);self.assertEqual(lower['balanceBytes'],0)
            # Settle prior overrun BEFORE a new credit; it never eats a later purchase.
            self.a.balance(c,self.uid,self.counters[self.uid]);c.execute('INSERT INTO live_payment_credits VALUES(?,?,?,0)',('topup',self.uid,50000000000))
            p=self.a.balance(c,self.uid,self.counters[self.uid]);self.assertEqual(p['paidBalanceBytes'],50000000000)
            c.execute('UPDATE live_payment_credits SET bytes=0');p=self.a.balance(c,self.uid,self.counters[self.uid]);self.assertEqual(p['paidBalanceBytes'],0)

    def test_paid_and_protected_accounts_are_untouched(self):
        with self.a.db() as c:
            c.execute('INSERT INTO live_payment_credits VALUES(?,?,?,0)',('existing',self.other,50000000000))
            c.execute('INSERT INTO live_payment_usage_baselines VALUES(?,?,0)',(self.other,777))
            for uid in [self.other,self.admin]:
                with self.assertRaises(HTTPException):self.a.claim(c,uid)
            self.assertEqual(c.execute('SELECT bytes FROM live_payment_credits').fetchone()[0],50000000000)
            self.assertEqual(c.execute('SELECT usage_bytes FROM live_payment_usage_baselines').fetchone()[0],777)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM trial_traffic_packages').fetchone()[0],0)
            c.execute('INSERT INTO vpn_imports VALUES(?,1)',(self.uid,))
            with self.assertRaises(HTTPException):self.a.claim(c,self.uid)

    def test_billing_credit_hook_settles_before_credit_and_is_idempotent(self):
        fixture=(ROOT/'tests/trials/fixtures/grant_credit.py').read_text()
        fixture=patch_billing(fixture)
        ns={'usage':lambda c,u:self.counters[u],'time':__import__('time')};exec(fixture,ns);ns['TRIAL_WALLET']=self.a
        with self.a.db() as c:
            self.a.claim(c,self.uid);self.counters[self.uid]+=2000000000
            row={'reference':'payment','user_id':self.uid,'gb':50}
            ns['grant_credit'](c,row);p=self.a.balance(c,self.uid);self.assertEqual(p['paidBalanceBytes'],50000000000)
            ns['grant_credit'](c,row);self.assertEqual(c.execute('SELECT COUNT(*) FROM live_payment_credits').fetchone()[0],1)

    def test_deletion_remembers_only_target_public_identities(self):
        device=str(uuid.uuid4())
        with self.a.db() as c:
            self.a.claim(c,self.uid)
            c.execute('INSERT INTO vpn_access VALUES(?,?)',(self.uid,'user_'+self.uid.replace('-','')))
            c.execute('INSERT INTO windows_devices VALUES(?,?,?,?)',(device,self.uid,'user_'+device.replace('-',''),'active'))
            c.execute('DELETE FROM windows_devices WHERE user_id=?',(self.uid,));c.execute('DELETE FROM vpn_access WHERE user_id=?',(self.uid,));c.execute('DELETE FROM users WHERE id=?',(self.uid,))
            identities=[r[0] for r in c.execute('SELECT identity FROM trial_access_identities WHERE user_id=?',(self.uid,))]
            self.assertIn('CN=tolf-win-'+device.replace('-','')+'.tolf.is',identities)
            self.assertIsNotNone(c.execute('SELECT 1 FROM trial_traffic_packages WHERE user_id=?',(self.uid,)).fetchone())
            self.assertEqual(c.execute('SELECT COUNT(*) FROM trial_access_identities WHERE user_id=?',(self.other,)).fetchone()[0],0)

    def test_registration_and_claim_guards_are_atomic_and_account_scoped(self):
        app=FastAPI()
        def marker(c,uid,payload,source):
            if payload.get('registrationPurpose')=='trial':c.execute('INSERT OR IGNORE INTO account_trial_registrations VALUES(?,?,?)',(uid,'2026-10-26',source))
        def guard(request):
            if request.headers.get('origin')!='https://vpn.tolf.is':raise HTTPException(403,'origin')
        def auth(request):
            if request.headers.get('test-auth')!='yes':raise HTTPException(401,'auth')
            return self.uid
        accounts=SimpleNamespace(record_trial=marker,guard=guard)
        app.state.account_management=accounts
        context={'DB':self.path,'authenticated_user_id':auth,'tolf_promos':SimpleNamespace(account_operation=lambda *args:nullcontext()),'tolf_billing_live':SimpleNamespace(TRIAL_WALLET=None)}
        fake=SimpleNamespace(totals=lambda c,start:self.counters)
        with patch.dict(sys.modules,{'tolf_traffic_policy':fake}):
            module.install(app,context)
            with self.a.db() as c:context['record_trial_registration'](c,self.other,{},'password')
            with self.assertRaises(RuntimeError):
                with self.a.db() as c:
                    context['record_trial_registration'](c,self.uid,{'registrationPurpose':'trial'},'passkey')
                    raise RuntimeError('registration failed after grant')
            with self.a.db() as c:
                self.assertEqual(c.execute('SELECT COUNT(*) FROM trial_traffic_packages').fetchone()[0],0)
                self.assertEqual(c.execute('SELECT COUNT(*) FROM account_trial_registrations').fetchone()[0],0)
            claim=next(r.endpoint for r in app.routes if r.path=='/account/trial-package' and 'POST' in r.methods)
            status=next(r.endpoint for r in app.routes if r.path=='/account/trial-package' and 'GET' in r.methods)
            def request(origin='https://vpn.tolf.is',authenticated=True):return Request({'type':'http','headers':[(b'origin',origin.encode()),(b'test-auth',b'yes' if authenticated else b'no')]})
            for req,payload,code in [(request(authenticated=False),{'confirm':'CLAIM_TRIAL'},401),(request(origin='https://example.com'),{'confirm':'CLAIM_TRIAL'},403),(request(),{'confirm':'CLAIM_TRIAL','user_id':self.other},400)]:
                with self.assertRaises(HTTPException) as error:claim(req,payload)
                self.assertEqual(error.exception.status_code,code)
            first=json.loads(claim(request(),{'confirm':'CLAIM_TRIAL'}).body)
            repeated=json.loads(claim(request(),{'confirm':'CLAIM_TRIAL'}).body)
            self.assertEqual(first['trialPackage']['balanceBytes'],1000000000)
            self.assertEqual(first['trialPackage']['grantedAt'],repeated['trialPackage']['grantedAt'])
            self.assertIn('no-store',status(request()).headers['cache-control'])
            with self.a.db() as c:
                self.assertEqual(c.execute('SELECT COUNT(*) FROM trial_traffic_packages').fetchone()[0],1)
                self.assertIsNone(self.a.balance(c,self.other))

    def test_snapshot_only_enrols_explicit_trials_and_restores_paid_access(self):
        with self.a.db() as c:
            self.a.claim(c,self.uid)
            c.execute('INSERT INTO vpn_access VALUES(?,?)',(self.uid,'user_'+self.uid.replace('-','')))
            c.execute('INSERT INTO vpn_access VALUES(?,?)',(self.other,'user_'+self.other.replace('-','')))
        fake=SimpleNamespace(totals=lambda c,start:self.counters)
        with patch.dict(sys.modules,{'tolf_traffic_policy':fake}):
            first=module.snapshot(self.path)
            self.assertEqual(first['principals'],[]);self.assertIn('user_'+self.uid.replace('-',''),first['allTrialPrincipals'])
            self.assertNotIn('user_'+self.other.replace('-',''),first['allTrialPrincipals'])
            self.counters[self.uid]+=1100000000
            self.assertIn('user_'+self.uid.replace('-',''),module.snapshot(self.path)['principals'])
            with self.a.db() as c:c.execute('INSERT INTO live_payment_credits VALUES(?,?,?,0)',('purchase',self.uid,50000000000))
            self.assertEqual(module.snapshot(self.path)['allTrialPrincipals'],[])


class NativeTests(unittest.TestCase):
    def row(self,identity,peer='198.51.100.1'):
        return {'state':b'ESTABLISHED','remote-eap-id':identity.encode(),'remote-host':peer.encode(),'child-sas':{'child':{'state':b'INSTALLED','spi-in':b'12345678','spi-out':b'87654321'}}}

    def test_authenticated_identity_and_peer_are_required(self):
        row=self.row('ordinary');row['remote-id']=b'trial'
        self.assertEqual(native.ike_spis([row],{'trial'}),(set(),set()))
        incoming,outgoing=native.ike_spis([self.row('trial'),self.row('ordinary','198.51.100.2')],{'trial'})
        self.assertEqual(incoming,{(0x12345678,'198.51.100.1')});self.assertEqual(outgoing,{(0x87654321,'198.51.100.1')})
        script=native.rules(incoming,outgoing,{123},{'203.0.113.1'},False)
        self.assertIn('ipsec out ip daddr 198.51.100.1',script);self.assertNotIn('198.51.100.2',script)
        self.assertIn('tcp dport 443 accept',script);self.assertIn('counter drop',script)

    def test_interface_reuse_and_other_users_are_not_blocked(self):
        first=[{'ID':7,'Username':'trial','Device':'vpns1','State':'connected'}]
        other=[{'ID':8,'Username':'ordinary','Device':'vpns1','State':'connected'}]
        self.assertEqual(native.oc_ifindices(first,other,{'trial'},{'vpns1':99}),set())
        self.assertEqual(native.oc_ifindices(first,first,{'trial'},{'vpns1':99}),{99})
        self.assertEqual(native.rules(set(),set(),set(),[],False),'')
        self.assertEqual(native.rules(set(),set(),set(),[],True),'delete table inet tolf_trial_budget\n')

    def test_expired_trial_lease_closes_only_enrolled_identities(self):
        with tempfile.TemporaryDirectory() as d:
            config=Path(d)/'config.json';state=Path(d)/'state.json'
            config.write_text(json.dumps({'version':1,'principals':[],'allTrialPrincipals':['trial'],'validUntil':1,'controlIPv4':['203.0.113.1']}))
            commands=[]
            def run(argv,**kwargs):commands.append((argv,kwargs));return SimpleNamespace(returncode=0,stdout=b'',stderr=b'')
            with patch.object(native,'CONFIG',config),patch.object(native,'STATE',state),patch.object(native,'inventory',return_value=[self.row('trial'),self.row('ordinary','198.51.100.2')]),patch.object(native,'oc_interfaces',return_value=set()),patch.object(native.subprocess,'run',side_effect=run):
                native._apply()
            actual=b'\n'.join(kw.get('input',b'') for argv,kw in commands)
            self.assertIn(b'198.51.100.1',actual);self.assertNotIn(b'198.51.100.2',actual)


if __name__=='__main__':unittest.main(verbosity=2)
