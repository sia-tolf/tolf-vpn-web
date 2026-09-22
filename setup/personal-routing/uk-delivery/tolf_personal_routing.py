"""Account-owned desired routing policies. Delivery is restricted to the enrolled Moscow account."""
import ipaddress
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import tolf_routing_delivery as delivery

VERSION = 1
EXITS = ("riga", "moscow", "usa")
AVAILABLE = ("riga", "moscow")
MAX_DOMAINS = 200
MAX_BODY = 131072


def connect(db):
    con = sqlite3.connect(db, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def initialize(db):
    with closing(connect(db)) as con, con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS vpn_personal_routing (
                user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                vpn_username TEXT NOT NULL,
                revision INTEGER NOT NULL CHECK (revision > 0),
                rules_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        columns = {row["name"] for row in con.execute("PRAGMA table_info(vpn_personal_routing)")}
        if "groups_json" not in columns:
            con.execute("ALTER TABLE vpn_personal_routing ADD COLUMN groups_json TEXT")


def domain_name(value):
    if not isinstance(value, str) or not value or len(value) > 253:
        raise HTTPException(400, "Invalid routing domain")
    value = value.strip().lower().rstrip(".")
    if any(c in value for c in "/:@*?#%\\"):
        raise HTTPException(400, "Enter a domain, not a URL or IP address")
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError:
        raise HTTPException(400, "Invalid routing domain") from None
    try:
        ipaddress.ip_address(value)
    except ValueError:
        pass
    else:
        raise HTTPException(400, "IP rules are not supported in this version")
    labels = value.split(".")
    if (len(value) > 253 or len(labels) < 2 or labels[-1].isdigit()
            or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", x)
                   for x in labels)):
        raise HTTPException(400, "Invalid routing domain")
    for label in labels:
        if label.startswith("xn--"):
            try:
                label.encode("ascii").decode("idna")
            except UnicodeError:
                raise HTTPException(400, "Invalid international domain") from None
    return value


def validate_rules(rules):
    if not isinstance(rules, dict) or set(rules) - set(EXITS):
        raise HTTPException(400, "Invalid routing exit groups")
    result = {key: [] for key in EXITS}
    count = 0
    for key in EXITS:
        values = rules.get(key, [])
        if not isinstance(values, list):
            raise HTTPException(400, "Each routing group must be a list")
        count += len(values)
        if count > MAX_DOMAINS:
            raise HTTPException(400, "Maximum 200 routing domains per account")
        if key not in AVAILABLE and values:
            raise HTTPException(400, "USA exit is not available yet")
        result[key] = sorted({domain_name(value) for value in values})
    assigned = [(domain, key) for key, values in result.items() for domain in values]
    for index, (domain, key) in enumerate(assigned):
        for other, other_key in assigned[index + 1:]:
            if key != other_key and (domain == other or domain.endswith("." + other)
                                     or other.endswith("." + domain)):
                raise HTTPException(409, "Domain and its subdomains cannot use different exits")
    return result


def validate_groups(value, rules):
    if not isinstance(value, dict) or set(value) != set(EXITS):
        raise HTTPException(400, "Invalid routing groups")
    result = {}
    count = 0
    for key in EXITS:
        groups = value[key]
        if not isinstance(groups, list) or len(groups) > MAX_DOMAINS:
            raise HTTPException(400, "Invalid routing groups")
        result[key] = []
        seen = set()
        for group in groups:
            if not isinstance(group, list) or not group:
                raise HTTPException(400, "Routing groups must be nonempty lists")
            count += len(group)
            if count > MAX_DOMAINS:
                raise HTTPException(400, "Maximum 200 routing domains per account")
            normalized = [domain_name(domain) for domain in group]
            if len(set(normalized)) != len(normalized) or seen.intersection(normalized):
                raise HTTPException(400, "Duplicate grouped domain")
            seen.update(normalized)
            result[key].append(normalized)
        if seen != set(rules[key]):
            raise HTTPException(400, "Routing groups must match routing rules")
    return result


def stored_groups(row, rules):
    if row and row["groups_json"]:
        return json.loads(row["groups_json"])
    return {key: [[domain] for domain in rules[key]] for key in EXITS}


def reconcile_groups(row, rules):
    old_rules = json.loads(row["rules_json"]) if row else {key: [] for key in EXITS}
    old = stored_groups(row, old_rules)
    result = {}
    for key in EXITS:
        remaining = set(rules[key])
        result[key] = []
        for group in old[key]:
            retained = [domain for domain in group if domain in remaining]
            if retained:
                result[key].append(retained)
                remaining.difference_update(retained)
        result[key].extend([[domain] for domain in rules[key] if domain in remaining])
    return result


def snapshot(row):
    rules = json.loads(row["rules_json"]) if row else {key: [] for key in EXITS}
    return {
        "groupingAvailable": True,
        "routingGroups": stored_groups(row, rules),
        "protocol": VERSION,
        "revision": row["revision"] if row else 0,
        "routingRules": json.loads(row["rules_json"]) if row else {key: [] for key in EXITS},
        "updatedAt": row["updated_at"] if row else None,
        "availableExits": list(AVAILABLE),
        "includeSubdomains": True,
        "maxDomains": MAX_DOMAINS,
        "enforcementAvailable": False,
        "appliedRevision": None,
        "state": "pending" if row else "not_configured",
    }


def current_vpn(con, user_id):
    row = con.execute("""SELECT v.vpn_username FROM vpn_access v
        JOIN users u ON u.id=v.user_id WHERE v.user_id=?""", (user_id,)).fetchone()
    if not row or not row["vpn_username"]:
        raise HTTPException(409, "VPN access is not configured")
    return row["vpn_username"]


def get_policy(db, user_id):
    with closing(connect(db)) as con:
        username = current_vpn(con, user_id)
        row = con.execute("SELECT * FROM vpn_personal_routing WHERE user_id=?", (user_id,)).fetchone()
        return delivery.enrich(con, user_id, username, snapshot(row))


def save_policy(db, user_id, payload):
    if (not isinstance(payload, dict) or not {"revision", "routingRules"} <= set(payload)
            or set(payload) - {"revision", "routingRules", "routingGroups"}):
        raise HTTPException(400, "Expected revision and routingRules")
    expected = payload["revision"]
    if type(expected) is not int or not 0 <= expected < 2**53 - 1:
        raise HTTPException(400, "Invalid routing revision")
    rules = validate_rules(payload["routingRules"])
    groups = validate_groups(payload["routingGroups"], rules) if "routingGroups" in payload else None
    encoded = json.dumps(rules, sort_keys=True, separators=(",", ":"))
    with closing(connect(db)) as con, con:
        con.execute("BEGIN IMMEDIATE")
        username = current_vpn(con, user_id)
        row = con.execute("SELECT * FROM vpn_personal_routing WHERE user_id=?", (user_id,)).fetchone()
        revision = row["revision"] if row else 0
        if expected != revision:
            raise HTTPException(409, "Routing policy changed; reload before saving")
        if groups is None:
            groups = reconcile_groups(row, rules)
        groups_encoded = json.dumps(groups, sort_keys=True, separators=(",", ":"))
        # Repeated identical saves need not create another pending revision.
        if (row and row["rules_json"] == encoded and row["vpn_username"] == username
                and stored_groups(row, rules) == groups):
            return snapshot(row)
        now = datetime.now(timezone.utc).isoformat()
        con.execute("""INSERT INTO vpn_personal_routing
            (user_id,vpn_username,revision,rules_json,updated_at,groups_json) VALUES (?,?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET vpn_username=excluded.vpn_username,
            revision=excluded.revision,rules_json=excluded.rules_json,updated_at=excluded.updated_at,
            groups_json=excluded.groups_json
            """, (user_id, username, revision + 1, encoded, now, groups_encoded))
        row = con.execute("SELECT * FROM vpn_personal_routing WHERE user_id=?", (user_id,)).fetchone()
        return snapshot(row)


async def read_payload(request):
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise HTTPException(415, "JSON content type required")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > MAX_BODY:
            raise HTTPException(413, "Routing request is too large")
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError):
        raise HTTPException(400, "Invalid JSON") from None


def install(app, context):
    db = context["DB"]
    auth = context["authenticated_user_id"]
    origins = {context["ORIGIN"], "https://tolf.is"}
    initialize(db)

    @app.get("/vpn/routing-rules")
    def read_rules(request: Request):
        data = get_policy(db, auth(request))
        return JSONResponse(data, headers={"Cache-Control": "private, no-store"})

    @app.post("/vpn/routing-rules")
    async def write_rules(request: Request):
        user_id = auth(request)
        if request.headers.get("origin") not in origins:
            raise HTTPException(403, "Untrusted request origin")
        payload = await read_payload(request)
        # Share the existing per-account provisioning lock.
        with context["tolf_promos"].account_operation(db, user_id):
            save_policy(db, user_id, payload)
            data = get_policy(db, user_id)
        return JSONResponse(data, headers={"Cache-Control": "private, no-store"})
