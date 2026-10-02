"""UK foundation for personal AnyConnect; issuance stays disabled until node activation."""
from contextlib import closing
from pathlib import Path
import sqlite3
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, Response
from tolf_oc_certificates import Authority

VERSION = 1
HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
SCHEMA = """
CREATE TABLE IF NOT EXISTS oc_devices (
    id TEXT PRIMARY KEY,
    -- Keep the certificate tombstone after account deletion for CRL enforcement.
    user_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    label TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    serial TEXT UNIQUE NOT NULL,
    certificate BLOB NOT NULL,
    encrypted_key BLOB NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('pending','active','revoking','revoked')),
    revoked_at TEXT,
    mode TEXT NOT NULL DEFAULT 'auto' CHECK(mode IN ('auto','ru','lv','yt')),
    UNIQUE(user_id, request_id)
);
CREATE TABLE IF NOT EXISTS oc_import_grants (
    token_hash BLOB PRIMARY KEY,
    device_id TEXT NOT NULL REFERENCES oc_devices(id),
    user_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    package BLOB NOT NULL
);
CREATE TRIGGER IF NOT EXISTS oc_after_account_delete AFTER DELETE ON users
BEGIN
    UPDATE oc_devices SET state='revoking',
        revoked_at=COALESCE(revoked_at,strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        WHERE user_id=OLD.id AND state IN ('pending','active');
    DELETE FROM oc_import_grants WHERE user_id=OLD.id;
END;
"""


def install(app, context):
    for name in ("DB", "authenticated_user_id", "tolf_promos"):
        if name not in context:
            raise RuntimeError("Missing TOLF integration: " + name)
    directory = Path(context["DB"]).parent / "anyconnect"
    authority = Authority(directory)
    with closing(sqlite3.connect(context["DB"], timeout=30)) as con, con:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone():
            raise RuntimeError("TOLF account database not found")
        con.executescript(SCHEMA)

    @app.get("/oc/access/capabilities")
    def capabilities():
        return JSONResponse({
            "version": VERSION, "certificateAuthority": True,
            "caSha256": authority.fingerprint,
            "issuance": False, "nodeReady": False,
            "reason": "node_activation_required",
        }, headers=HEADERS)

    @app.get("/oc/access/ca.pem")
    def public_ca():
        # This is a public CA certificate, never a key or a client identity.
        return Response((directory / "ca.pem").read_bytes(),
                        media_type="application/x-pem-file", headers=HEADERS)

    @app.get("/oc/access/devices")
    def devices(request: Request):
        user = context["authenticated_user_id"](request)
        with closing(sqlite3.connect(context["DB"], timeout=30)) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("""
                SELECT id,label,username,created_at,expires_at,state,mode
                FROM oc_devices WHERE user_id=? ORDER BY created_at
            """, (user,)).fetchall()
        return JSONResponse({"devices": [dict(row) for row in rows]}, headers=HEADERS)

    @app.post("/oc/access/devices")
    def create_device(request: Request):
        context["authenticated_user_id"](request)
        if request.headers.get("origin") != context.get("ORIGIN"):
            raise HTTPException(403, "Invalid origin")
        raise HTTPException(503, "AnyConnect node activation is not completed")
