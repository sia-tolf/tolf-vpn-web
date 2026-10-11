"""Temporary UK-only iOS AnyConnect combined-profile pilot.

Never store completed profiles or PKCS12 cleartext in public document roots.
"""

import plistlib
import uuid
from tolf_oc_shortcuts import vpn_name


def make_combined_profile(row, authority, ingress, entry_name, production=False, include_buttons=False):
    if ingress not in ("oc.tolf.is:4443", "oc-riga.tolf.is:443"):
        raise ValueError("Unsupported ingress")
    entry_id = {"oc.tolf.is:4443": "moscow", "oc-riga.tolf.is:443": "riga"}[ingress]
    pkcs12_bytes, pkcs12_password = authority.bundle(row)
    if production:
        # Stable per-device, per-entry identity: reinstall updates only this entry.
        def stable(kind):
            return str(uuid.uuid5(uuid.NAMESPACE_URL, "https://tolf.is/ios/anyconnect/" + row["id"] + "/" + entry_id + "/" + kind)).upper()
        cert_uuid = stable("certificate")
        vpn_uuid = stable("vpn")
        profile_uuid = stable("profile")
        prefix = "is.tolf.anyconnect.ios."
    else:
        cert_uuid = str(uuid.uuid4()).upper()
        vpn_uuid = str(uuid.uuid4()).upper()
        profile_uuid = str(uuid.uuid4()).upper()
        prefix = "is.tolf.anyconnect.combined."
    device_suffix = row["id"].replace("-", "")
    label = str(row["label"])[:36]

    certificate = {
        "PayloadType": "com.apple.security.pkcs12",
        "PayloadVersion": 1,
        "PayloadIdentifier": prefix + "identity." + device_suffix + "." + cert_uuid.lower(),
        "PayloadUUID": cert_uuid,
        "PayloadDisplayName": "TOLF AnyConnect certificate — " + label,
        "PayloadContent": pkcs12_bytes,
        "Password": pkcs12_password,
        "PayloadCertificateFileName": "TOLF-AnyConnect.p12",
    }

    vpn = {
        "PayloadType": "com.apple.vpn.managed",
        "PayloadVersion": 1,
        "PayloadIdentifier": prefix + "vpn." + device_suffix + "." + vpn_uuid.lower(),
        "PayloadUUID": vpn_uuid,
        "PayloadDisplayName": vpn_name(row, entry_name) + ("" if production else " (combined)"),
        "UserDefinedName": vpn_name(row, entry_name) + ("" if production else " (combined)"),
        "VPNType": "VPN",
        "VPNSubType": "com.cisco.anyconnect",
        "VPN": {
            "RemoteAddress": ingress,
            "AuthenticationMethod": "Certificate",
            "ProviderType": "packet-tunnel",
            "PayloadCertificateUUID": cert_uuid,
            "OnDemandEnabled": 1 if production else 0,
            "DisconnectOnIdle": 0,
            **({"OnDemandRules": [{"Action": "Connect"}]} if production else {}),
        },
    }

    profile = {
        "PayloadType": "Configuration",
        "PayloadVersion": 1,
        "PayloadIdentifier": prefix + "config." + device_suffix + "." + profile_uuid.lower(),
        "PayloadUUID": profile_uuid,
        "PayloadDisplayName": vpn_name(row, entry_name) if production else "TOLF AnyConnect — combined test",
        "PayloadDescription": (
            "TOLF Cisco Secure Client: device certificate, VPN connection and automatic On Demand."
            if production else
            "TOLF iOS pilot: linked existing device certificate and new Cisco VPN entry. On Demand is off to preserve the existing working VPN."
        ),
        "PayloadOrganization": "TOLF",
        "PayloadRemovalDisallowed": False,
        "PayloadContent": [certificate, vpn],
    }
    if include_buttons:
        from tolf_oc_webclips import webclip_payloads
        profile["PayloadContent"].extend(webclip_payloads(row["id"], entry_id=entry_id))
    return plistlib.dumps(profile, fmt=plistlib.FMT_XML, sort_keys=False)


def register_combined_test(app, authenticate, record, authority, database, enabled_nodes):
    """Authenticated token issuance, short-lived unauthenticated Safari download."""
    import datetime as dt
    import hashlib
    import re
    import secrets
    import sqlite3

    from contextlib import closing
    from fastapi import HTTPException, Request
    from fastapi.responses import JSONResponse, Response

    create_table = """
    CREATE TABLE IF NOT EXISTS oc_combined_pilot_grants (
        token_hash BLOB PRIMARY KEY,
        device_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        ingress TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        download_count INTEGER NOT NULL DEFAULT 0
    )
    """
    with closing(sqlite3.connect(database, timeout=20)) as con, con:
        con.execute(create_table)

    def is_valid_row(con, token):
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise HTTPException(404, "Profile not found")
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        con.row_factory = sqlite3.Row
        row = con.execute("""
            SELECT d.*, g.ingress FROM oc_combined_pilot_grants g
            JOIN oc_devices d ON d.id=g.device_id AND d.user_id=g.user_id
            JOIN users u ON u.id=g.user_id
            WHERE g.token_hash=? AND g.expires_at>?
              AND g.download_count<4
              AND d.state='active' AND d.expires_at>?
        """, (hashlib.sha256(token.encode()).digest(), now, now)).fetchone()
        if row is None:
            raise HTTPException(410, "Profile link expired or no longer valid")
        return row

    @app.get("/oc/access/devices/{device_id}/ios.mobileconfig")
    def download_ios_profile(device_id: str, request: Request, ingress: str = "moscow", buttons: bool = False):
        # A direct HTTPS link from vpn.tolf.is; no bearer token or PKCS12 file
        # ever appears in the URL. The active TOLF session authorizes download.
        user = authenticate(request)
        if ingress not in enabled_nodes:
            raise HTTPException(400, "Entry point not enabled")
        row = record(user, device_id, True)
        name = "Москва" if ingress == "moscow" else "Рига"
        host = {"moscow": "oc.tolf.is:4443", "riga": "oc-riga.tolf.is:443"}[ingress]
        unsigned = make_combined_profile(row, authority, host, name, production=True, include_buttons=buttons)
        # Signing uses the same TOLF signing authority as iOS IKEv2 and DNS profiles.
        from tolf_profiles import _sign_apple_profile
        signed = _sign_apple_profile(unsigned)
        return Response(signed, media_type="application/x-apple-aspen-config", headers={
            "Cache-Control": "private, no-store, no-transform",
            "Content-Disposition": 'attachment; filename="TOLF-AnyConnect.mobileconfig"',
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        })


    @app.get("/oc/access/devices/{device_id}/shortcuts/{mode}.shortcut")
    def download_ios_shortcut(device_id: str, mode: str, request: Request, ingress: str = "moscow"):
        user = authenticate(request)
        if ingress not in enabled_nodes or mode not in ("on", "off", "control"):
            raise HTTPException(400, "Unsupported shortcut or entry point")
        row = record(user, device_id, True)
        from tolf_oc_shortcuts import signed_shortcut, vpn_name
        name = vpn_name(row, "Москва" if ingress == "moscow" else "Рига")
        try:
            signed = signed_shortcut(name, mode)
        except Exception:
            raise HTTPException(503, "Shortcut signing temporarily unavailable") from None
        return Response(signed, media_type="application/x-apple-shortcut", headers={
            "Cache-Control": "private, no-store, no-transform",
            "Content-Disposition": 'inline; filename="' + ("TOLF" if mode == "control" else "TOLF-" + mode.upper()) + '.shortcut"',
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        })

    @app.post("/oc/access/devices/{device_id}/combined-pilot")
    async def issue_combined_pilot(device_id: str, request: Request):
        # This pilot setup page is served from the same api.tolf.is origin.
        if request.headers.get("origin") != "https://api.tolf.is":
            raise HTTPException(403, "Invalid origin")
        if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
            raise HTTPException(415, "JSON required")
        data = await request.json()
        if type(data) is not dict or set(data) != {"ingress"}:
            raise HTTPException(400, "Unexpected fields")
        ingress = data["ingress"]
        if ingress not in enabled_nodes:
            raise HTTPException(400, "Entry point not enabled")
        user = authenticate(request)
        device = record(user, device_id, True)
        token = secrets.token_urlsafe(32)
        expires = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=8)).isoformat()
        with closing(sqlite3.connect(database, timeout=20)) as con, con:
            con.execute("DELETE FROM oc_combined_pilot_grants WHERE device_id=? OR expires_at<=?",
                        (device["id"], dt.datetime.now(dt.timezone.utc).isoformat()))
            con.execute("""
                INSERT INTO oc_combined_pilot_grants
                (token_hash,device_id,user_id,ingress,expires_at,download_count)
                VALUES(?,?,?,?,?,0)
            """, (hashlib.sha256(token.encode()).digest(),
                  device["id"], user, ingress, expires))
        return JSONResponse({
            "url": "https://api.tolf.is/oc/access/combined-pilot/" + token + ".mobileconfig",
            "expiresAt": expires,
            "deviceLabel": device["label"],
            "ingress": ingress,
        }, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})

    @app.head("/oc/access/combined-pilot/{token}.mobileconfig")
    def head_combined_pilot(token: str):
        with closing(sqlite3.connect(database, timeout=20)) as con:
            is_valid_row(con, token)
        return Response(headers={
            "Cache-Control": "private, no-store",
            "Content-Type": "application/x-apple-aspen-config",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        })

    @app.get("/oc/access/combined-pilot/{token}.mobileconfig")
    def get_combined_pilot(token: str):
        with closing(sqlite3.connect(database, timeout=20)) as con, con:
            con.execute("BEGIN IMMEDIATE")
            row = is_valid_row(con, token)
            con.execute("""
                UPDATE oc_combined_pilot_grants
                SET download_count=download_count+1
                WHERE token_hash=?
            """, (hashlib.sha256(token.encode()).digest(),))
        name = "Москва" if row["ingress"] == "moscow" else "Рига"
        ingress_host = {"moscow": "oc.tolf.is:4443", "riga": "oc-riga.tolf.is:443"}[row["ingress"]]
        body = make_combined_profile(row, authority, ingress_host, name)
        return Response(body, media_type="application/x-apple-aspen-config", headers={
            "Cache-Control": "private, no-store, no-transform",
            "Content-Disposition": 'attachment; filename="TOLF-AnyConnect-Combined-Test.mobileconfig"',
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        })
