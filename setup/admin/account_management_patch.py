"""Prepare narrow source edits without replacing unrelated installed API changes."""
import ast


def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Unsupported API source anchor: ' + old[:70])
    return source.replace(old, new, 1)


def admin_source(source):
    function = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'user_record')
    returned = next(n for n in function.body if isinstance(n, ast.Return))
    lines = source.splitlines(keepends=True)
    block = ''.join(lines[returned.lineno-1:returned.end_lineno])
    replacement = block.replace('    return ', '    result = ', 1) + "    if CTX.get('account_admin_metadata'):\n        result.update(CTX['account_admin_metadata'](con, user_id))\n    return result\n"
    source = source.replace(block, replacement, 1)
    source = once(source, "def users(request: Request, q: str = '', offset: int = 0, limit: int = 50):", "def users(request: Request, q: str = '', offset: int = 0, limit: int = 50, trial: str = 'all'):")
    source = once(source, '        q = q.strip()\n', "        if trial not in ('all','only'):\n            raise HTTPException(400, 'invalid_trial_filter')\n        q = q.strip()\n")
    source = once(source, '        args = (q,q,q,q,q)\n', "        args = (q,q,q,q,q)\n        if trial == 'only':\n            if not CTX.get('account_admin_metadata'):\n                raise HTTPException(503, 'account_management_unavailable')\n            where += ' AND EXISTS(SELECT 1 FROM account_trial_registrations tr WHERE tr.user_id=u.id)'\n")
    compile(source, 'tolf_admin.py', 'exec')
    return source


def password_source(source):
    old = "            response = session(con, uid, {'username':login, 'recoveryCode':code})\n"
    new = "            if ns.get('record_trial_registration'):\n                ns['record_trial_registration'](con, uid, payload, 'password')\n            elif payload.get('registrationPurpose') is not None:\n                raise HTTPException(503, 'trial_registration_unavailable')\n" + old
    source = once(source, old, new)
    compile(source, 'tolf_password_auth.py', 'exec')
    return source


def main_source(source):
    start = source.index('@app.post("/account/delete")')
    end = source.index('@app.post("/vpn/create")', start)
    original = source[start:end]
    block_start = original.index('    with tolf_promos.account_operation(DB, user_id):')
    response_start = original.index('    response = JSONResponse(', block_start)
    body = original[block_start:response_start]
    body = once(body, '    with tolf_promos.account_operation(DB, user_id):', '    with (nullcontext() if lock_held else tolf_promos.account_operation(DB, user_id)):')
    helper = 'def delete_account_data(user_id, lock_held=False):\n    from contextlib import nullcontext\n' + body
    helper += "    reconcile = globals().get('oc_reconcile_account')\n    if reconcile:\n        try:\n            reconcile(user_id)\n        except Exception:\n            pass  # Persisted revocation tombstones are retried by the existing worker.\n\n\n"
    route = original[:block_start] + '    delete_account_data(user_id)\n' + original[response_start:]
    source = source[:start] + helper + route + source[end:]
    marker = '@app.post("/passkey/register/finish")'
    start = source.index(marker)
    end = source.index('@app.get("/qr/', start)
    section = source[start:end]
    anchor = '            con.execute("DELETE FROM challenges WHERE id=?", (challenge_id,))\n'
    section = once(section, anchor, "            if globals().get('record_trial_registration'):\n                record_trial_registration(con, user_id, body, 'passkey')\n            elif body.get('registrationPurpose') is not None:\n                raise HTTPException(503, 'trial_registration_unavailable')\n" + anchor)
    source = source[:start] + section + source[end:]
    source += '\n# Explicit trial registrations and administrator account lifecycle.\nimport tolf_account_admin\ntolf_account_admin.install(app, globals())\n'
    compile(source, 'main.py', 'exec')
    return source


def anyconnect_source(source):
    source = once(source, '    def reconcile():\n', '    def reconcile(user_id=None):\n')
    old = '''                con.execute("UPDATE oc_devices SET state='revoking',revoked_at=COALESCE(revoked_at,?) WHERE state IN ('pending','active') AND (expires_at<=? OR NOT EXISTS (SELECT 1 FROM users WHERE id=oc_devices.user_id))", (utc_now().isoformat(),utc_now().isoformat()))'''
    new = '''                con.execute("UPDATE oc_devices SET state='revoking',revoked_at=COALESCE(revoked_at,?) WHERE state IN ('pending','active') AND (expires_at<=? OR NOT EXISTS (SELECT 1 FROM users WHERE id=oc_devices.user_id)) AND (? IS NULL OR user_id=?)", (utc_now().isoformat(),utc_now().isoformat(),user_id,user_id))'''
    source = once(source, old, new)
    source = once(source, '''                rows = con.execute("SELECT id,username FROM oc_devices WHERE state='revoking'").fetchall()''', '''                rows = con.execute("SELECT id,username FROM oc_devices WHERE state='revoking' AND (? IS NULL OR user_id=?)", (user_id,user_id)).fetchall()''')
    source = once(source, '    def reconcile_policies():\n', "    context['oc_reconcile_account'] = reconcile\n\n    def reconcile_policies():\n")
    compile(source, 'tolf_anyconnect.py', 'exec')
    return source


def prepare(sources):
    if 'tolf_account_admin.install(app, globals())' in sources['main.py']:
        raise ValueError('Account management is already installed; inspect before updating')
    return {'main.py':main_source(sources['main.py']), 'tolf_admin.py':admin_source(sources['tolf_admin.py']),
            'tolf_password_auth.py':password_source(sources['tolf_password_auth.py']), 'tolf_anyconnect.py':anyconnect_source(sources['tolf_anyconnect.py'])}
