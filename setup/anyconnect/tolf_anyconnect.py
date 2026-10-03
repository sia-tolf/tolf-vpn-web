"""UK foundation for personal AnyConnect; issuance stays disabled until node activation."""
from contextlib import closing, asynccontextmanager
from pathlib import Path
import datetime as dt
import fcntl
import os
import sqlite3
import tempfile
import asyncio
import hashlib
import json
import logging
import re
import secrets
import subprocess
import threading
import time
import uuid
from urllib.parse import urlencode, quote
from starlette.concurrency import run_in_threadpool
from cryptography import x509
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, Response
from tolf_oc_certificates import Authority

VERSION = 2
RECONCILE_INTERVAL = 60
HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
MODES = {"auto", "ru", "lv", "yt"}
SSH = ["/usr/bin/ssh", "-T", "-i", "/opt/tolf-api/provision_ed25519",
       "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
       "-o", "UserKnownHostsFile=/opt/tolf-api/.ssh/known_hosts", "-o", "ConnectTimeout=10",
       "root@92.243.66.204"]


class Node:
    def __init__(self, fingerprint, runner=None):
        self.fingerprint = fingerprint
        self.runner = runner
        self.lock = threading.Lock()
        self.checked = 0
        self.ready = False

    def call(self, command):
        try:
            if self.runner is not None:
                data = self.runner(command)
            else:
                result = subprocess.run(SSH + [command], capture_output=True, text=True, timeout=25)
                if result.returncode or len(result.stdout) > 16384:
                    raise ValueError("Node operation failed")
                data = json.loads(result.stdout)
            if not isinstance(data, dict) or data.get("status") != "ok":
                raise ValueError("Invalid node acknowledgement")
            return data
        except (OSError, subprocess.TimeoutExpired, ValueError):
            raise HTTPException(503, "AnyConnect node unavailable") from None

    def health(self, fresh=False):
        with self.lock:
            if not fresh and time.monotonic() - self.checked < 10:
                return self.ready
            self.ready = False
            try:
                self.check_health(self.call("tolf-oc-node-health"))
                self.ready = True
            except HTTPException:
                pass
            self.checked = time.monotonic()
            return self.ready

    def check_health(self, data):
        if (data.get("version") != 1 or data.get("caSha256") != self.fingerprint
                or data.get("deviceRouting") is not True):
            raise HTTPException(503, "AnyConnect node trust mismatch")

    def identity(self, username):
        if not re.fullmatch(r"tolf-oc-[0-9a-f]{32}", username):
            raise HTTPException(503, "Invalid device identity")

    def set(self, username, mode):
        self.identity(username)
        if mode not in MODES:
            raise HTTPException(400, "Invalid routing mode")
        data = self.call(f"tolf-oc-device {username} {mode}")
        if data.get("username") != username or data.get("mode") != mode:
            raise HTTPException(503, "Device policy not acknowledged")

    def remove(self, username):
        self.identity(username)
        data = self.call(f"tolf-oc-device-remove {username}")
        if data.get("username") != username or data.get("removed") is not True:
            raise HTTPException(503, "Device revocation not acknowledged")

    def session(self, username):
        self.identity(username)
        data = self.call(f"tolf-oc-session {username}")
        if data.get("username") != username or type(data.get("connected")) is not bool:
            raise HTTPException(503, "Invalid device session response")
        return data["connected"]

    def sync_crl(self):
        self.check_health(self.call("tolf-oc-crl-sync"))


async def payload(request, required):
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise HTTPException(415, "JSON required")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 4096:
            raise HTTPException(413, "Request too large")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError):
        raise HTTPException(400, "Invalid JSON") from None
    if not isinstance(data, dict) or set(data) != set(required):
        raise HTTPException(400, "Unexpected request fields")
    return data


def canonical_id(value):
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(400, "Invalid device identifier") from None


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def device_public(row):
    return {key: row[key] for key in ("id", "request_id", "label", "username", "created_at", "expires_at", "state", "mode")}
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
CREATE TABLE IF NOT EXISTS oc_setup_links (
    token_hash BLOB PRIMARY KEY,
    device_id TEXT NOT NULL REFERENCES oc_devices(id),
    user_id TEXT NOT NULL,
    expires_at TEXT NOT NULL
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
    node = Node(authority.fingerprint, context.get("OC_REMOTE"))
    db = context["DB"]

    def activated():
        try:
            value = json.loads((directory / "activation.json").read_text())
            return value == {"enabled": True, "caSha256": authority.fingerprint}
        except (OSError, ValueError):
            return False

    def ensure_ready():
        if not activated() or not node.health(fresh=True):
            raise HTTPException(503, "AnyConnect node activation is not completed")

    def authenticate(request, mutate=False):
        user = context["authenticated_user_id"](request)
        if mutate and request.headers.get("origin") != "https://vpn.tolf.is":
            raise HTTPException(403, "Invalid origin")
        return user

    def record(user, device_id, active=False):
        with closing(sqlite3.connect(db, timeout=30)) as con:
            con.row_factory = sqlite3.Row
            row = con.execute("SELECT * FROM oc_devices WHERE id=? AND user_id=?", (canonical_id(device_id), user)).fetchone()
        if row is None:
            raise HTTPException(404, "Device not found")
        if active and (row["state"] != "active" or dt.datetime.fromisoformat(row["expires_at"]) <= utc_now()):
            raise HTTPException(409, "Device access is not active")
        return row

    def reconcile():
        fd = os.open(directory / "reconcile.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return
            with closing(sqlite3.connect(db, timeout=30)) as con, con:
                con.execute("UPDATE oc_devices SET state='revoking',revoked_at=COALESCE(revoked_at,?) WHERE state IN ('pending','active') AND (expires_at<=? OR NOT EXISTS (SELECT 1 FROM users WHERE id=oc_devices.user_id))", (utc_now().isoformat(),utc_now().isoformat()))
                rows = con.execute("SELECT id,username FROM oc_devices WHERE state='revoking'").fetchall()
            if not rows:
                return
            published_crl(authority, directory, db)
            node.sync_crl()
            for device_id, username in rows:
                node.remove(username)
                with closing(sqlite3.connect(db, timeout=30)) as con, con:
                    con.execute("UPDATE oc_devices SET state='revoked' WHERE id=? AND state='revoking'", (device_id,))
        finally:
            os.close(fd)

    # Revocations caused by account deletion are retried, including after restart.
    periodic_task = None

    async def periodic():
        while True:
            await asyncio.sleep(RECONCILE_INTERVAL)
            try:
                await run_in_threadpool(reconcile)
                with closing(sqlite3.connect(db, timeout=30)) as con, con:
                    con.execute("DELETE FROM oc_import_grants WHERE expires_at<=?", (utc_now().isoformat(),))
                    con.execute("DELETE FROM oc_setup_links WHERE expires_at<=? OR NOT EXISTS (SELECT 1 FROM users WHERE id=oc_setup_links.user_id)", (utc_now().isoformat(),))
            except Exception:
                logging.getLogger(__name__).warning("AnyConnect revocation retry failed")

    async def startup():
        nonlocal periodic_task
        periodic_task = asyncio.create_task(periodic())

    async def shutdown():
        if periodic_task is not None:
            periodic_task.cancel()
            try:
                await periodic_task
            except asyncio.CancelledError:
                pass

    previous_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        async with previous_lifespan(application) as state:
            await startup()
            try:
                yield state
            finally:
                await shutdown()

    app.router.lifespan_context = lifespan
    with closing(sqlite3.connect(context["DB"], timeout=30)) as con, con:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone():
            raise RuntimeError("TOLF account database not found")
        con.executescript(SCHEMA)

    @app.get("/oc/access/capabilities")
    def capabilities():
        enabled = activated()
        ready = enabled and node.health()
        return JSONResponse({
            "version": VERSION, "certificateAuthority": True,
            "caSha256": authority.fingerprint,
            "issuance": ready, "nodeReady": ready,
            "guestSetup": True,
            "reason": "ready" if ready else ("node_unavailable" if enabled else "node_activation_required"),
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
        user = authenticate(request)
        with closing(sqlite3.connect(context["DB"], timeout=30)) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("""
                SELECT id,request_id,label,username,created_at,expires_at,state,mode
                FROM oc_devices WHERE user_id=? ORDER BY created_at
            """, (user,)).fetchall()
        return JSONResponse({"devices": [dict(row) for row in rows]}, headers=HEADERS)

    @app.post("/oc/access/devices")
    async def create_device(request: Request):
        user = authenticate(request, True)
        await run_in_threadpool(ensure_ready)
        data = await payload(request, {"requestId", "label"})
        request_id = canonical_id(data["requestId"])
        label = data["label"]
        if not isinstance(label, str) or not 1 <= len(label.strip()) <= 80 or any(ord(c) < 32 for c in label):
            raise HTTPException(400, "Invalid device name")

        def operation():
            with context["tolf_promos"].account_operation(db, user):
                with closing(sqlite3.connect(db, timeout=30)) as con:
                    con.row_factory = sqlite3.Row
                    row = con.execute("SELECT * FROM oc_devices WHERE user_id=? AND request_id=?", (user, request_id)).fetchone()
                    count = con.execute("SELECT count(*) FROM oc_devices WHERE user_id=? AND state IN ('pending','active','revoking') AND expires_at>?", (user, utc_now().isoformat())).fetchone()[0]
                if row is None:
                    if count >= 8:
                        raise HTTPException(409, "Device limit reached")
                    device_id = str(uuid.uuid4())
                    issued = authority.issue(device_id)
                    with closing(sqlite3.connect(db, timeout=30)) as con, con:
                        con.execute("""INSERT INTO oc_devices
                            (id,user_id,request_id,label,username,serial,certificate,encrypted_key,created_at,expires_at,state)
                            VALUES (?,?,?,?,?,?,?,?,?,?,'pending')""",
                            (device_id,user,request_id,label.strip(),issued["username"],issued["serial"],issued["certificate"],issued["encrypted_key"],issued["created_at"],issued["expires_at"]))
                    row = record(user, device_id)
                if row["state"] not in {"pending", "active"}:
                    raise HTTPException(409, "This creation request was revoked")
                if row["label"] != label.strip() or dt.datetime.fromisoformat(row["expires_at"]) <= utc_now():
                    raise HTTPException(409, "Creation request changed or expired")
                if row["state"] == "pending":
                    node.set(row["username"], row["mode"])
                    with closing(sqlite3.connect(db, timeout=30)) as con, con:
                        updated = con.execute("UPDATE oc_devices SET state='active' WHERE id=? AND state='pending' AND EXISTS (SELECT 1 FROM users WHERE id=oc_devices.user_id)", (row["id"],)).rowcount
                    if updated != 1:
                        node.remove(row["username"])
                        raise HTTPException(409, "Account changed during issuance")
                return JSONResponse({"device": device_public(record(user, row["id"]))}, headers=HEADERS)
        return await run_in_threadpool(operation)

    def package_response(row, package, password, token, expires):
        url = "https://api.tolf.is/oc/access/import/" + token + ".p12"
        connection_name = "TOLF " + row["label"][:10] + " " + row["id"].replace("-", "")[-8:]
        create = "anyconnect://create/?" + urlencode({"name":connection_name, "host":"oc.tolf.is:4443", "usecert":"true", "certcommonname":row["username"], "netroam":"true"}, quote_via=quote)
        return {"deviceId":row["id"], "label":row["label"], "certificateUrl":url, "password":password, "expiresAt":expires,
                "importUri":"anyconnect://import/?" + urlencode({"type":"pkcs12", "uri":url}, quote_via=quote),
                "connectionUri":create, "connectionName":connection_name, "server":"oc.tolf.is:4443", "username":row["username"]}

    def setup_record(con, token):
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise HTTPException(404, "Setup link not found")
        con.row_factory = sqlite3.Row
        row = con.execute("""SELECT d.*, s.expires_at AS setup_expires FROM oc_setup_links s
            JOIN oc_devices d ON d.id=s.device_id AND d.user_id=s.user_id JOIN users u ON u.id=d.user_id
            WHERE s.token_hash=? AND s.expires_at>? AND d.state='active' AND d.expires_at>?""",
            (hashlib.sha256(token.encode()).digest(), utc_now().isoformat(), utc_now().isoformat())).fetchone()
        if row is None:
            raise HTTPException(410, "Setup link expired, revoked or already used")
        return row

    @app.post("/oc/access/devices/{device_id}/setup-link")
    def create_setup_link(device_id: str, request: Request):
        user = authenticate(request, True)
        ensure_ready()
        with context["tolf_promos"].account_operation(db, user):
            row = record(user, device_id, True)
            token = secrets.token_urlsafe(32)
            expires = (utc_now() + dt.timedelta(hours=24)).isoformat()
            with closing(sqlite3.connect(db, timeout=30)) as con, con:
                con.execute("DELETE FROM oc_setup_links WHERE device_id=? OR expires_at<=?", (row["id"], utc_now().isoformat()))
                con.execute("INSERT INTO oc_setup_links VALUES (?,?,?,?)", (hashlib.sha256(token.encode()).digest(), row["id"], user, expires))
            return JSONResponse({"deviceId":row["id"], "expiresAt":expires,
                                 "setupUrl":"https://vpn.tolf.is/anyconnect-setup.html#" + token}, headers=HEADERS)

    @app.get("/oc/access/setup/{token}")
    def setup_info(token: str):
        with closing(sqlite3.connect(db, timeout=30)) as con:
            row = setup_record(con, token)
        info = package_response(row, None, None, "", row["setup_expires"])
        return JSONResponse({key:info[key] for key in ("label", "connectionUri", "connectionName", "server", "expiresAt")}, headers=HEADERS)

    @app.post("/oc/access/setup/{token}/claim")
    def claim_setup(token: str, request: Request):
        if request.headers.get("origin") != "https://vpn.tolf.is":
            raise HTTPException(403, "Invalid origin")
        with closing(sqlite3.connect(db, timeout=30)) as con:
            owner = setup_record(con, token)["user_id"]
        ensure_ready()
        with context["tolf_promos"].account_operation(db, owner):
            with closing(sqlite3.connect(db, timeout=30)) as con, con:
                con.execute("BEGIN IMMEDIATE")
                row = setup_record(con, token)
                package, password = authority.bundle(row)
                import_token = secrets.token_urlsafe(32)
                expires = (utc_now() + dt.timedelta(hours=2)).isoformat()
                con.execute("DELETE FROM oc_setup_links WHERE token_hash=?", (hashlib.sha256(token.encode()).digest(),))
                con.execute("DELETE FROM oc_import_grants WHERE device_id=? OR expires_at<=?", (row["id"], utc_now().isoformat()))
                con.execute("INSERT INTO oc_import_grants VALUES (?,?,?,?,?)", (hashlib.sha256(import_token.encode()).digest(), row["id"], owner, expires, package))
            return JSONResponse(package_response(row, package, password, import_token, expires), headers=HEADERS)

    @app.post("/oc/access/devices/{device_id}/import")
    def import_grant(device_id: str, request: Request):
        user = authenticate(request, True)
        ensure_ready()
        with context["tolf_promos"].account_operation(db, user):
            row = record(user, device_id, True)
            package, password = authority.bundle(row)
            token = secrets.token_urlsafe(32)
            expires = (utc_now() + dt.timedelta(hours=2)).isoformat()
            with closing(sqlite3.connect(db, timeout=30)) as con, con:
                con.execute("DELETE FROM oc_import_grants WHERE device_id=? OR expires_at<=?", (row["id"], utc_now().isoformat()))
                con.execute("INSERT INTO oc_import_grants VALUES (?,?,?,?,?)", (hashlib.sha256(token.encode()).digest(), row["id"], user, expires, package))
            return JSONResponse(package_response(row, package, password, token, expires), headers=HEADERS)

    @app.get("/oc/access/import/{token}.p12")
    def download(token: str):
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise HTTPException(404, "Import link not found")
        token_hash = hashlib.sha256(token.encode()).digest()
        with closing(sqlite3.connect(db, timeout=30)) as con, con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("""SELECT g.package FROM oc_import_grants g
                JOIN oc_devices d ON d.id=g.device_id JOIN users u ON u.id=d.user_id
                WHERE g.token_hash=? AND g.expires_at>? AND d.state='active' AND d.expires_at>?""",
                (token_hash,utc_now().isoformat(),utc_now().isoformat())).fetchone()
            if row is None:
                raise HTTPException(410, "Import link expired or already used")
            con.execute("DELETE FROM oc_import_grants WHERE token_hash=?", (token_hash,))
        return Response(row[0], media_type="application/x-pkcs12", headers={**HEADERS,"Content-Disposition":'attachment; filename="TOLF-AnyConnect.p12"'})

    @app.head("/oc/access/import/{token}.p12")
    def inspect_download(token: str):
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise HTTPException(404, "Import link not found")
        with closing(sqlite3.connect(db, timeout=30)) as con:
            row = con.execute("""SELECT length(g.package) FROM oc_import_grants g
                JOIN oc_devices d ON d.id=g.device_id JOIN users u ON u.id=d.user_id
                WHERE g.token_hash=? AND g.expires_at>? AND d.state='active' AND d.expires_at>?""",
                (hashlib.sha256(token.encode()).digest(),utc_now().isoformat(),utc_now().isoformat())).fetchone()
        if row is None:
            raise HTTPException(410, "Import link expired or already used")
        return Response(media_type="application/x-pkcs12", headers={**HEADERS,"Content-Length":str(row[0])})

    @app.get("/oc/access/devices/{device_id}/policy")
    def get_policy(device_id: str, request: Request):
        row = record(authenticate(request), device_id, True)
        return JSONResponse({"username":row["username"],"mode":row["mode"],"applied":True}, headers=HEADERS)

    @app.post("/oc/access/devices/{device_id}/policy")
    async def set_policy(device_id: str, request: Request):
        user = authenticate(request, True)
        data = await payload(request, {"mode"})
        if not isinstance(data["mode"], str) or data["mode"] not in MODES:
            raise HTTPException(400, "Invalid routing mode")
        def operation():
            with context["tolf_promos"].account_operation(db, user):
                row = record(user, device_id, True)
                node.set(row["username"], data["mode"])
                with closing(sqlite3.connect(db, timeout=30)) as con, con:
                    updated = con.execute("UPDATE oc_devices SET mode=? WHERE id=? AND state='active' AND EXISTS (SELECT 1 FROM users WHERE id=oc_devices.user_id)", (data["mode"],row["id"])).rowcount
                if updated != 1:
                    node.remove(row["username"])
                    raise HTTPException(409, "Account changed during policy update")
                return JSONResponse({"username":row["username"],"mode":data["mode"],"applied":True}, headers=HEADERS)
        return await run_in_threadpool(operation)

    @app.get("/oc/access/devices/{device_id}/session")
    def get_session(device_id: str, request: Request):
        row = record(authenticate(request), device_id, True)
        return JSONResponse({"username":row["username"],"mode":row["mode"],"connected":node.session(row["username"])}, headers=HEADERS)

    @app.post("/oc/access/devices/{device_id}/revoke")
    def revoke(device_id: str, request: Request):
        user = authenticate(request, True)
        with context["tolf_promos"].account_operation(db, user):
            row = record(user, device_id)
            with closing(sqlite3.connect(db, timeout=30)) as con, con:
                con.execute("UPDATE oc_devices SET state='revoking',revoked_at=COALESCE(revoked_at,?) WHERE id=? AND state IN ('pending','active')", (utc_now().isoformat(),row["id"]))
                con.execute("DELETE FROM oc_import_grants WHERE device_id=?", (row["id"],))
                con.execute("DELETE FROM oc_setup_links WHERE device_id=?", (row["id"],))
            try:
                reconcile()
            except HTTPException:
                pass  # Persist the request; background retries it until acknowledged.
            row = record(user, row["id"])
            return JSONResponse({"device":device_public(row)}, status_code=200 if row["state"] == "revoked" else 202, headers=HEADERS)
