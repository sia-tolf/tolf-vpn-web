"""UK foundation for personal AnyConnect; issuance stays disabled until node activation."""
from contextlib import closing
from pathlib import Path
import datetime as dt
import fcntl
import os
import sqlite3
import tempfile
from cryptography import x509
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


def published_crl(authority, directory, db):
    """Refresh signed public CRL under a process-wide lock; never undo a revocation."""
    fd = os.open(directory / "crl.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        path = directory / "ca.crl.pem"
        previous = path.read_bytes()
        crl = x509.load_pem_x509_crl(previous)
        if crl.issuer != authority.cert.subject or not crl.is_signature_valid(authority.cert.public_key()):
            raise RuntimeError("Stored AnyConnect CRL signature is invalid")
        revoked = {entry.serial_number: entry.revocation_date_utc for entry in crl}
        with closing(sqlite3.connect(db, timeout=30)) as con:
            rows = con.execute("SELECT serial,revoked_at FROM oc_devices WHERE state IN ('revoking','revoked')").fetchall()
        for serial, revoked_at in rows:
            when = dt.datetime.fromisoformat(revoked_at.replace("Z", "+00:00"))
            if when.tzinfo is None:
                raise RuntimeError("Revocation timestamp must include timezone")
            revoked.setdefault(int(serial, 16), when)
        now = dt.datetime.now(dt.timezone.utc)
        if len(revoked) == len(crl) and crl.next_update_utc > now + dt.timedelta(days=1):
            return previous
        number = crl.extensions.get_extension_for_class(x509.CRLNumber).value.crl_number + 1
        data = authority.crl([(format(serial, "x"), when) for serial, when in sorted(revoked.items())], number)
        temporary_fd, temporary = tempfile.mkstemp(prefix=".crl-", dir=directory)
        try:
            with os.fdopen(temporary_fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return data
    finally:
        os.close(fd)


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

    @app.get("/oc/access/crl.pem")
    def public_crl():
        try:
            data = published_crl(authority, directory, context["DB"])
        except (OSError, ValueError, RuntimeError, sqlite3.Error):
            raise HTTPException(503, "AnyConnect revocation list unavailable") from None
        return Response(data, media_type="application/x-pem-file", headers=HEADERS)

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
