@app.post("/account/delete")
def account_delete(request: Request, payload: dict | None = None):
    user_id = authenticated_user_id(request)
    if (payload or {}).get("confirm") != "DELETE":
        raise HTTPException(400, "Account deletion not confirmed")
    with tolf_promos.account_operation(DB, user_id):
        tolf_invitations.before_account_delete(user_id)
        tolf_windows.delete_all(user_id)
        row = vpn_record(user_id)
        # Also recover from a previous create which completed remotely but lost its response.
        remove_provisioned_vpn(user_id, row[0] if row else None)
        provision_on_riga("revoke-moscow", user_id)
        con = sqlite3.connect(DB)
        try:
            con.execute("BEGIN")
            row = con.execute("SELECT webauthn_user_id FROM users WHERE id=?", (user_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Account not found")
            con.execute("DELETE FROM challenges WHERE user_id=? OR (webauthn_user_id IS NOT NULL AND webauthn_user_id=?)", (user_id, row[0]))
            tolf_promos.detach_account(con, user_id)
            for table in ("windows_devices", "vpn_imports", "vpn_access", "passkeys", "sessions"):
                con.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
            deleted = con.execute("DELETE FROM users WHERE id=?", (user_id,))
            if deleted.rowcount != 1:
                raise RuntimeError("Account disappeared during deletion")
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
    response = JSONResponse({"status": "ok", "deleted": True})
    response.delete_cookie(key=SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    return response


@app.post("/vpn/create")
def vpn_create():
    pass

@app.post("/passkey/register/finish")
async def passkey_register_finish(request: Request):
    body = await request.json()
    challenge_id, credential = body.get("challengeId"), body.get("credential")
    if not challenge_id or not credential:
        raise HTTPException(400, "Missing registration data")
    con = sqlite3.connect(DB)
    try:
        row = con.execute("SELECT user_id,challenge,webauthn_user_id,passkey_name FROM challenges WHERE id=? AND kind='register'", (challenge_id,)).fetchone()
        if not row:
            raise HTTPException(400, "Registration challenge not found")
        user_id, challenge, webauthn_user_id, passkey_name = row
        if not passkey_name:
            raise HTTPException(400, "Passkey name not found")
        try:
            verification = verify_registration_response(credential=credential, expected_challenge=challenge,
                expected_rp_id=RP_ID, expected_origin=ORIGIN, require_user_verification=True)
        except Exception as exc:
            raise HTTPException(400, "Passkey verification failed") from exc
        recovery_code = generate_recovery_code()
        try:
            con.execute("INSERT INTO users(id,created_at,webauthn_user_id,recovery_code_hash) VALUES (?,?,?,?)", (user_id,utc_iso(utc_now()),webauthn_user_id,recovery_code_hash(recovery_code)))
            con.execute("INSERT INTO passkeys(credential_id,user_id,public_key,sign_count,created_at,name) VALUES (?,?,?,?,?,?)",
                        (verification.credential_id,user_id,verification.credential_public_key,verification.sign_count,utc_iso(utc_now()),passkey_name))
            con.execute("DELETE FROM challenges WHERE id=?", (challenge_id,))
            con.commit()
        except sqlite3.IntegrityError as exc:
            con.rollback()
            raise HTTPException(409, "Passkey already registered") from exc
    finally:
        con.close()
    return tolf_quick.registration_session({"status":"ok", "userId":user_id, "passkeyName":passkey_name, "recoveryCode":recovery_code}, globals())


@app.get("/qr/{token}.svg")
def qr_svg():
    pass

