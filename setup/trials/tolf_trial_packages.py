"""One-time trial traffic and a wallet scoped only to explicit trial recipients."""
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

BYTES = 1_000_000_000
HEADERS = {'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'}


class Trials:
    def __init__(self, context, usage=None):
        self.ctx=context
        self.usage=usage or self.current_usage
        with self.db() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS trial_traffic_packages(
              user_id TEXT PRIMARY KEY,
              granted_bytes INTEGER NOT NULL CHECK(granted_bytes=1000000000),
              granted_at REAL NOT NULL,observed_total INTEGER NOT NULL,
              consumed_bytes INTEGER NOT NULL DEFAULT 0,unfunded_bytes INTEGER NOT NULL DEFAULT 0,
              updated_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS trial_access_sync(
              node TEXT PRIMARY KEY,revision TEXT NOT NULL,applied_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS trial_access_identities(
              user_id TEXT NOT NULL,identity TEXT NOT NULL,PRIMARY KEY(user_id,identity));
            ''')
            if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='vpn_access'").fetchone():
                c.executescript('''CREATE TRIGGER IF NOT EXISTS trial_save_vpn_identity BEFORE DELETE ON vpn_access
                  BEGIN INSERT OR IGNORE INTO trial_access_identities SELECT OLD.user_id,OLD.vpn_username
                    WHERE OLD.vpn_username IS NOT NULL AND EXISTS(SELECT 1 FROM trial_traffic_packages WHERE user_id=OLD.user_id); END;''')
            if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='windows_devices'").fetchone():
                c.executescript('''CREATE TRIGGER IF NOT EXISTS trial_save_windows_identity BEFORE DELETE ON windows_devices
                  BEGIN
                   INSERT OR IGNORE INTO trial_access_identities SELECT OLD.user_id,'tolf-win-'||replace(OLD.id,'-','')||'.tolf.is' WHERE EXISTS(SELECT 1 FROM trial_traffic_packages WHERE user_id=OLD.user_id);
                   INSERT OR IGNORE INTO trial_access_identities SELECT OLD.user_id,'CN=tolf-win-'||replace(OLD.id,'-','')||'.tolf.is' WHERE EXISTS(SELECT 1 FROM trial_traffic_packages WHERE user_id=OLD.user_id);
                   INSERT OR IGNORE INTO trial_access_identities SELECT OLD.user_id,OLD.username WHERE OLD.username IS NOT NULL AND EXISTS(SELECT 1 FROM trial_traffic_packages WHERE user_id=OLD.user_id);
                  END;''')

    @contextmanager
    def db(self):
        c=sqlite3.connect(self.ctx['DB'],timeout=30);c.row_factory=sqlite3.Row
        try:
            with c:yield c
        finally:c.close()

    @staticmethod
    def current_usage(c,uid):
        from tolf_traffic_policy import totals
        return totals(c,'1970-01-01T00:00:00+00:00').get(uid,0)

    @staticmethod
    def paid(c,uid):
        return c.execute('SELECT COALESCE(SUM(bytes),0) FROM live_payment_credits WHERE user_id=?',(uid,)).fetchone()[0]

    def eligibility(self,c,uid):
        if not c.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone():return 'account_not_found'
        if c.execute('SELECT 1 FROM trial_traffic_packages WHERE user_id=?',(uid,)).fetchone():return None
        if c.execute('SELECT 1 FROM admin_roles WHERE user_id=?',(uid,)).fetchone():return 'administrator_account'
        if c.execute('SELECT 1 FROM vpn_imports WHERE user_id=? AND protected=1',(uid,)).fetchone():return 'protected_account'
        if c.execute("SELECT 1 FROM managed_users WHERE account_id=? AND source!='site' AND deleted_at IS NULL",(uid,)).fetchone():return 'existing_vpn_account'
        if self.paid(c,uid)>0:return 'paid_account'
        return None

    def claim(self,c,uid):
        reason=self.eligibility(c,uid)
        if reason:raise HTTPException(409,'trial_'+reason)
        if not c.execute('SELECT 1 FROM trial_traffic_packages WHERE user_id=?',(uid,)).fetchone():
            current=self.usage(c,uid)
            if type(current) is not int or current<0:raise HTTPException(503,'trial_usage_unavailable')
            now=time.time()
            c.execute('INSERT INTO trial_traffic_packages VALUES(?,?,?,?,0,0,?)',(uid,BYTES,now,current,now))
        return self.balance(c,uid)

    def balance(self,c,uid,current=None):
        row=c.execute('SELECT * FROM trial_traffic_packages WHERE user_id=?',(uid,)).fetchone()
        if not row:return None
        # Public reads use the settled wallet. The worker and credit hook supply fresh counters.
        if current is None:current=row['observed_total']
        if type(current) is not int or current<0:raise HTTPException(503,'trial_usage_unavailable')
        paid=self.paid(c,uid);entitlement=row['granted_bytes']+paid
        delta=max(0,current-row['observed_total'])
        consumed=min(row['consumed_bytes'],entitlement)
        charge=min(delta,max(0,entitlement-consumed))
        consumed+=charge;unfunded=row['unfunded_bytes']+delta-charge
        if delta or consumed!=row['consumed_bytes']:
            c.execute('UPDATE trial_traffic_packages SET observed_total=?,consumed_bytes=?,unfunded_bytes=?,updated_at=? WHERE user_id=?',
                      (max(row['observed_total'],current),consumed,unfunded,time.time(),uid))
        trial_used=min(row['granted_bytes'],consumed);paid_used=max(0,consumed-row['granted_bytes'])
        return {'grantedBytes':row['granted_bytes'],'grantedAt':row['granted_at'],
                'usedBytes':trial_used,'balanceBytes':max(0,row['granted_bytes']-trial_used),
                'paidCreditedBytes':paid,'paidUsedBytes':paid_used,'paidBalanceBytes':max(0,paid-paid_used),
                'availableBytes':max(0,entitlement-consumed),'state':'active' if entitlement>consumed else 'exhausted',
                'unfundedBytes':unfunded,'checkedAt':time.time()}

    def status(self,uid):
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            package=self.balance(c,uid)
            trial=c.execute('SELECT registered_at FROM account_trial_registrations WHERE user_id=?',(uid,)).fetchone()
            reason=self.eligibility(c,uid)
        return {'trialPackageIssuance':True,'trialPackage':package,'canClaim':package is None and reason is None,
                'reason':reason,'trialRegisteredAt':trial[0] if trial else None}


def install(app,context):
    trials=Trials(context);context['trial_wallet']=trials;app.state.trial_packages=trials
    accounts=app.state.account_management
    original=accounts.record_trial
    def record(c,uid,payload,source):
        original(c,uid,payload,source)
        if payload.get('registrationPurpose')=='trial':trials.claim(c,uid)
    accounts.record_trial=record
    context['record_trial_registration']=record
    # Settlement before a new credit prevents unpaid overrun being charged to a later purchase.
    context['tolf_billing_live'].TRIAL_WALLET=trials

    @app.get('/account/trial-package')
    def status(request:Request):
        return JSONResponse(trials.status(context['authenticated_user_id'](request)),headers=HEADERS)

    @app.post('/account/trial-package')
    def claim(request:Request,payload:dict):
        uid=context['authenticated_user_id'](request);accounts.guard(request)
        if payload!={'confirm':'CLAIM_TRIAL'}:raise HTTPException(400,'invalid_confirmation')
        with context['tolf_promos'].account_operation(context['DB'],uid):
            with trials.db() as c:
                c.execute('BEGIN IMMEDIATE');record(c,uid,{'registrationPurpose':'trial'},'existing_account')
        return JSONResponse(trials.status(uid),headers=HEADERS)


def snapshot(path):
    trials=Trials({'DB':path})
    from tolf_traffic_policy import totals
    identities=set();all_identities=set();exhausted=0
    with trials.db() as c:
        c.execute('BEGIN IMMEDIATE')
        users=[(r[0],r[1] is not None) for r in c.execute('SELECT t.user_id,u.id FROM trial_traffic_packages t LEFT JOIN users u ON u.id=t.user_id')]
        usage=totals(c,'1970-01-01T00:00:00+00:00') if any(exists for uid,exists in users) else {}
        for uid,exists in users:
            balance=trials.balance(c,uid,usage.get(uid,0)) if exists else None
            # Paid accounts retain the same access policy as existing paid-only accounts.
            if exists and balance['paidCreditedBytes']>0:continue
            account_identities={'user_'+uid.replace('-','')}
            account_identities.update(r[0] for r in c.execute('SELECT identity FROM trial_access_identities WHERE user_id=?',(uid,)))
            for row in c.execute('SELECT vpn_username FROM vpn_access WHERE user_id=?',(uid,)):
                if row[0]:account_identities.add(row[0])
            for row in c.execute("SELECT username FROM windows_devices WHERE user_id=? AND state!='deleted'",(uid,)):
                if row[0]:account_identities.add(row[0])
            for row in c.execute("SELECT id FROM windows_devices WHERE user_id=? AND state!='deleted'",(uid,)):
                cn='tolf-win-'+row[0].replace('-','')+'.tolf.is';account_identities.update((cn,'CN='+cn))
            for row in c.execute("SELECT username FROM oc_devices WHERE user_id=?",(uid,)):
                account_identities.add(row[0])
            if c.execute("SELECT 1 FROM ike_mobile_us WHERE user_id=?",(uid,)).fetchone():
                for mode in ('auto','ru','lv','yt'):
                    cn='tolf-mobile-'+uid.replace('-','')+'-'+mode+'.tolf.is';account_identities.update((cn,'CN='+cn))
            all_identities.update(account_identities)
            if not exists or balance['availableBytes']==0:
                exhausted+=1;identities.update(account_identities)
    import re
    # Legacy human-chosen VPN aliases can later be reassigned; never gate them.
    valid=re.compile(r'(?:user_[0-9a-f]{32}|tolf-oc-[0-9a-f]{32}|(?:CN=)?tolf-win-[0-9a-f]{32}\.tolf\.is|(?:CN=)?tolf-mobile-[0-9a-f]{32}-(?:auto|ru|lv|yt)\.tolf\.is)\Z')
    return {'principals':sorted(v for v in identities if isinstance(v,str) and valid.fullmatch(v)),
            'allTrialPrincipals':sorted(v for v in all_identities if isinstance(v,str) and valid.fullmatch(v)),
            'trialAccounts':sum(exists for uid,exists in users),'exhaustedAccounts':exhausted}


if __name__=='__main__':
    import json,sys
    if sys.argv[1:]!=['--snapshot']:raise SystemExit('invalid_arguments')
    print(json.dumps(snapshot('/var/lib/tolf-api/tolf.db'),separators=(',',':')))
