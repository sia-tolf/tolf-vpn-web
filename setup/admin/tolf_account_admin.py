"""Explicit trial registrations and administrator account deletion."""
import hashlib
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

HEADERS = {'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'}


class Accounts:
    def __init__(self, context):
        self.ctx = context
        self.path = context['DB']
        with self.db() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS account_trial_registrations(
              user_id TEXT PRIMARY KEY,registered_at TEXT NOT NULL,source TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS trial_registration_account_delete AFTER DELETE ON users
              BEGIN DELETE FROM account_trial_registrations WHERE user_id=OLD.id; END;
            CREATE TABLE IF NOT EXISTS admin_account_delete_jobs(
              request_id TEXT PRIMARY KEY,actor TEXT NOT NULL,target TEXT NOT NULL,number INTEGER NOT NULL,
              state TEXT NOT NULL,result TEXT,created REAL NOT NULL,updated REAL NOT NULL);
            ''')

    @contextmanager
    def db(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def admin(self, request):
        actor = self.ctx['authenticated_user_id'](request)
        with self.db() as c:
            if not c.execute('SELECT 1 FROM admin_roles WHERE user_id=?', (actor,)).fetchone():
                raise HTTPException(403, 'administrator_required')
        return actor

    def guard(self, request):
        if request.headers.get('origin') != self.ctx['ORIGIN'] or request.headers.get('content-type','').split(';')[0].strip() != 'application/json':
            raise HTTPException(403, 'invalid_origin')

    @staticmethod
    def canonical(value):
        try:
            return str(uuid.UUID(value))
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(400, 'invalid_identifier')

    @staticmethod
    def record_trial(c, uid, payload, source):
        purpose = payload.get('registrationPurpose')
        if purpose is None:
            return
        if purpose != 'trial':
            raise HTTPException(400, 'invalid_registration_purpose')
        if not c.execute('SELECT 1 FROM users WHERE id=?', (uid,)).fetchone():
            raise HTTPException(404, 'user_not_found')
        c.execute('INSERT OR IGNORE INTO account_trial_registrations VALUES(?,?,?)',
                  (uid, datetime.now(timezone.utc).isoformat(), source))

    def metadata(self, c, uid):
        trial = c.execute('SELECT registered_at,source FROM account_trial_registrations WHERE user_id=?', (uid,)).fetchone()
        paid = False
        if trial and c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='live_payment_credits'").fetchone():
            paid = bool(c.execute('SELECT 1 FROM live_payment_credits WHERE user_id=? LIMIT 1', (uid,)).fetchone())
        administrator = bool(c.execute('SELECT 1 FROM admin_roles WHERE user_id=?', (uid,)).fetchone())
        protected = bool(c.execute('SELECT 1 FROM vpn_imports WHERE user_id=? AND protected=1', (uid,)).fetchone())
        number = c.execute('SELECT MIN(number) FROM managed_users WHERE account_id=? AND deleted_at IS NULL', (uid,)).fetchone()[0]
        reason = 'administrator' if administrator else 'protected' if protected else 'missing_registry' if number is None else None
        return {'trialRegistration':{'registeredAt':trial['registered_at'],'source':trial['source'],'hasPaidTraffic':paid} if trial else None,
                'deletion':{'allowed':reason is None,'reason':reason}}

    def trial_summary(self):
        with self.db() as c:
            total = c.execute('SELECT COUNT(*) FROM account_trial_registrations t JOIN users u ON u.id=t.user_id').fetchone()[0]
            daily = [dict(r) for r in c.execute('SELECT substr(t.registered_at,1,10) AS day,COUNT(*) AS registrations FROM account_trial_registrations t JOIN users u ON u.id=t.user_id GROUP BY 1 ORDER BY 1 DESC LIMIT 90')]
        return {'activeTrialAccounts':total,'daily':daily,'trialPackageIssuance':False}

    def delete(self, request, target, payload):
        actor = self.admin(request)
        self.guard(request)
        target = self.canonical(target)
        if not isinstance(payload,dict) or set(payload) != {'requestId','confirm','number'} or payload.get('confirm') != 'DELETE' or type(payload.get('number')) is not int or payload['number'] < 1:
            raise HTTPException(400, 'invalid_confirmation')
        request_id = self.canonical(payload['requestId'])
        if target == actor:
            raise HTTPException(409, 'cannot_delete_self')
        with self.db() as c:
            job = c.execute('SELECT * FROM admin_account_delete_jobs WHERE request_id=?', (request_id,)).fetchone()
            if job:
                if (job['actor'],job['target'],job['number']) != (actor,target,payload['number']):
                    raise HTTPException(409, 'request_changed')
                if job['state'] == 'completed':
                    return json.loads(job['result']), 200
                # Recover a lost response/restart after the deletion transaction committed.
                if not c.execute('SELECT 1 FROM users WHERE id=?', (target,)).fetchone():
                    tombstone = c.execute('SELECT 1 FROM managed_users WHERE account_id=? AND number=? AND deleted_at IS NOT NULL', (target,payload['number'])).fetchone()
                    if tombstone:
                        pending = bool(c.execute("SELECT 1 FROM oc_devices WHERE user_id=? AND state='revoking' LIMIT 1", (target,)).fetchone())
                        result = {'status':'ok','deleted':True,'number':payload['number'],'vpnRevocationPending':pending,'requestId':request_id}
                        c.execute("UPDATE admin_account_delete_jobs SET state='completed',result=?,updated=? WHERE request_id=?", (json.dumps(result),time.time(),request_id))
                        c.execute('INSERT INTO admin_audit(actor,action,target,created_at) VALUES(?,?,?,?)', (actor,'account.delete.completed',target,datetime.now(timezone.utc).isoformat()))
                        return result, 200
                if job['state'] == 'running' and job['updated'] > time.time()-300:
                    return {'status':'pending','deleted':False,'requestId':request_id}, 202
        # All provisioning routes use this same cross-process account lock.
        with self.ctx['tolf_promos'].account_operation(self.path, target):
            self.admin(request)
            with self.db() as c:
                meta = self.metadata(c, target)
                if not meta['deletion']['allowed']:
                    raise HTTPException(409, 'cannot_delete_' + meta['deletion']['reason'])
                row = c.execute('SELECT MIN(number) FROM managed_users WHERE account_id=? AND deleted_at IS NULL', (target,)).fetchone()
                if row[0] != payload['number']:
                    raise HTTPException(409, 'account_number_changed')
                now = time.time()
                c.execute('INSERT INTO admin_account_delete_jobs VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(request_id) DO UPDATE SET state=excluded.state,updated=excluded.updated',
                          (request_id,actor,target,row[0],'running',None,now,now))
                c.execute('INSERT INTO admin_audit(actor,action,target,created_at) VALUES(?,?,?,?)', (actor,'account.delete.requested',target,datetime.now(timezone.utc).isoformat()))
            try:
                # Already holding the target's account lock; never substitute the actor's session.
                self.ctx['delete_account_data'](target, lock_held=True)
            except Exception:
                with self.db() as c:
                    c.execute("UPDATE admin_account_delete_jobs SET state='failed',updated=? WHERE request_id=?", (time.time(),request_id))
                    c.execute('INSERT INTO admin_audit(actor,action,target,created_at) VALUES(?,?,?,?)', (actor,'account.delete.failed',target,datetime.now(timezone.utc).isoformat()))
                raise HTTPException(502, 'account_delete_incomplete') from None
            with self.db() as c:
                pending = bool(c.execute("SELECT 1 FROM oc_devices WHERE user_id=? AND state='revoking' LIMIT 1", (target,)).fetchone())
                result = {'status':'ok','deleted':True,'number':payload['number'],'vpnRevocationPending':pending,'requestId':request_id}
                c.execute("UPDATE admin_account_delete_jobs SET state='completed',result=?,updated=? WHERE request_id=?", (json.dumps(result),time.time(),request_id))
                c.execute('INSERT INTO admin_audit(actor,action,target,created_at) VALUES(?,?,?,?)', (actor,'account.delete.completed',target,datetime.now(timezone.utc).isoformat()))
            return result, 200


def install(app, context):
    accounts = Accounts(context)
    context['record_trial_registration'] = accounts.record_trial
    context['account_admin_metadata'] = accounts.metadata
    app.state.account_management = accounts

    @app.get('/account/trial-registration')
    def trial_status(request: Request):
        uid = context['authenticated_user_id'](request)
        with accounts.db() as c:
            trial = accounts.metadata(c, uid)['trialRegistration']
        return JSONResponse({'trialRegistration':trial,'trialPackageIssuance':False}, headers=HEADERS)

    @app.post('/account/trial-registration')
    def trial_register(request: Request, payload: dict):
        uid = context['authenticated_user_id'](request)
        accounts.guard(request)
        if payload != {'confirm':'TRIAL_REGISTRATION'}:
            raise HTTPException(400, 'invalid_confirmation')
        with context['tolf_promos'].account_operation(context['DB'], uid):
            with accounts.db() as c:
                accounts.record_trial(c, uid, {'registrationPurpose':'trial'}, 'existing_account')
                trial = accounts.metadata(c, uid)['trialRegistration']
        return JSONResponse({'trialRegistration':trial,'trialPackageIssuance':False}, headers=HEADERS)

    @app.get('/admin/trial-registrations')
    def trials(request: Request):
        accounts.admin(request)
        return JSONResponse(accounts.trial_summary(), headers=HEADERS)

    @app.post('/admin/users/{user_id}/delete')
    def delete_user(user_id: str, request: Request, payload: dict):
        data, status = accounts.delete(request, user_id, payload)
        return JSONResponse(data, status_code=status, headers=HEADERS)

    @app.get('/admin/account-deletions/{request_id}')
    def deletion_status(request_id: str, request: Request):
        actor = accounts.admin(request)
        request_id = accounts.canonical(request_id)
        with accounts.db() as c:
            job = c.execute('SELECT state,result,number FROM admin_account_delete_jobs WHERE request_id=? AND actor=?', (request_id,actor)).fetchone()
        if not job:
            raise HTTPException(404, 'deletion_not_found')
        return JSONResponse(json.loads(job['result']) if job['state']=='completed' else {'status':job['state'],'deleted':False,'number':job['number']}, headers=HEADERS)
