AUTH = None

def grant_credit(c,row):
    if c.execute('SELECT 1 FROM live_payment_credits WHERE reference=?',(row['reference'],)).fetchone():return
    if not c.execute('SELECT 1 FROM live_payment_usage_baselines WHERE user_id=?',(row['user_id'],)).fetchone():
        c.execute('INSERT INTO live_payment_usage_baselines VALUES(?,?,?)',(row['user_id'],usage(c,row['user_id']),time.time()))
    else:
        current=usage(c,row['user_id'])
        prior=c.execute('SELECT COALESCE(SUM(bytes),0) FROM live_payment_credits WHERE user_id=?',(row['user_id'],)).fetchone()[0]
        c.execute('UPDATE live_payment_usage_baselines SET usage_bytes=MAX(usage_bytes,?) WHERE user_id=?',(current-prior,row['user_id']))
    c.execute('INSERT OR IGNORE INTO live_payment_credits VALUES(?,?,?,?)',(row['reference'],row['user_id'],row['gb']*1_000_000_000,time.time()))

def install(app):
    @app.get('/billing/live/account')
    def account(request:Request):
        uid=admin(request)
        with database() as c:
            rows=c.execute('SELECT * FROM live_payment_orders WHERE user_id=? ORDER BY created DESC LIMIT 30',(uid,)).fetchall()
            credits=c.execute('SELECT COALESCE(SUM(bytes),0) FROM live_payment_credits WHERE user_id=?',(uid,)).fetchone()[0]
            baseline=c.execute('SELECT usage_bytes FROM live_payment_usage_baselines WHERE user_id=?',(uid,)).fetchone()
            used=max(0,usage(c,uid)-baseline[0]) if baseline else 0
        return JSONResponse({'mode':'live','balanceBytes':max(0,credits-used),'creditedBytes':credits,'usedBytes':used,'orders':[public(r) for r in rows]},headers=HEADERS)

    @app.post('/billing/live/orders')
    def create_order():
        pass
