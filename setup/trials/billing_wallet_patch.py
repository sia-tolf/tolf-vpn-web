"""Integrate trial-first settlement without changing legacy paid-only accounts."""


def once(source,old,new):
    if source.count(old)!=1:raise ValueError('Unsupported billing source: '+old[:80])
    return source.replace(old,new,1)


def patch(source):
    source=once(source,'AUTH = None\n','AUTH = None\nTRIAL_WALLET = None\n')
    source=once(source,'def grant_credit(c,row):\n',"def grant_credit(c,row):\n    if TRIAL_WALLET is not None and c.execute('SELECT 1 FROM trial_traffic_packages WHERE user_id=?',(row['user_id'],)).fetchone():\n        TRIAL_WALLET.balance(c,row['user_id'],usage(c,row['user_id']))\n")
    start=source.index("    @app.get('/billing/live/account')")
    end=source.index("    @app.post('/billing/live/orders')",start)
    part=source[start:end]
    part=once(part,'        with database() as c:\n',"        with database() as c:\n            has_trial = TRIAL_WALLET is not None and c.execute('SELECT 1 FROM trial_traffic_packages WHERE user_id=?',(uid,)).fetchone()\n            if has_trial:c.execute('BEGIN IMMEDIATE')\n")
    part=once(part,'            used=max(0,usage(c,uid)-baseline[0]) if baseline else 0',"            wallet=TRIAL_WALLET.balance(c,uid) if has_trial else None\n            used=wallet['paidUsedBytes'] if wallet else max(0,usage(c,uid)-baseline[0]) if baseline else 0")
    source=source[:start]+part+source[end:]
    compile(source,'tolf_billing_live.py','exec')
    return source
