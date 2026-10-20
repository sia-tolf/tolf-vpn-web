import hashlib
import hmac
import json
import re
import sqlite3
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from tolf_oc_live import SCHEMA as OC_LIVE_SCHEMA, usage as oc_live_usage

USERNAME_RE = re.compile(r"^tolf-oc-[0-9a-f]{32}$")
SESSION_RE = re.compile(r"^[0-9]{1,20}$")
COMPLETIONS = {"normal", "recovered"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS oc_node_credentials (
    node_id TEXT PRIMARY KEY
        CHECK(length(node_id) BETWEEN 1 AND 24 AND substr(node_id,1,1) GLOB '[a-z]' AND node_id NOT GLOB '*[^a-z0-9-]*'),
    credential_hash BLOB NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE TABLE IF NOT EXISTS oc_traffic_sessions (
    node_id TEXT NOT NULL
        CHECK(length(node_id) BETWEEN 1 AND 24 AND substr(node_id,1,1) GLOB '[a-z]' AND node_id NOT GLOB '*[^a-z0-9-]*'),
    session_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    connected_at TEXT NOT NULL,
    disconnected_at TEXT NOT NULL,
    upload_bytes INTEGER NOT NULL CHECK(upload_bytes>=0),
    download_bytes INTEGER NOT NULL CHECK(download_bytes>=0),
    total_bytes INTEGER NOT NULL CHECK(total_bytes>=0),
    completion_type TEXT NOT NULL
        CHECK(completion_type IN ('normal','recovered')),
    received_at TEXT NOT NULL,
    PRIMARY KEY(node_id,session_id),
    FOREIGN KEY(device_id) REFERENCES oc_devices(id)
);
CREATE INDEX IF NOT EXISTS oc_traffic_user_time
ON oc_traffic_sessions(user_id,disconnected_at);
CREATE INDEX IF NOT EXISTS oc_traffic_device_time
ON oc_traffic_sessions(device_id,disconnected_at);

CREATE TABLE IF NOT EXISTS ike_traffic_sessions (
    node_id TEXT NOT NULL
        CHECK(length(node_id) BETWEEN 1 AND 24 AND substr(node_id,1,1) GLOB '[a-z]' AND node_id NOT GLOB '*[^a-z0-9-]*'),
    session_id TEXT NOT NULL,
    user_id TEXT,
    username TEXT NOT NULL,
    started_at TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    stopped_at TEXT,
    upload_bytes INTEGER NOT NULL DEFAULT 0
        CHECK(upload_bytes>=0),
    download_bytes INTEGER NOT NULL DEFAULT 0
        CHECK(download_bytes>=0),
    total_bytes INTEGER NOT NULL DEFAULT 0
        CHECK(total_bytes>=0),
    state TEXT NOT NULL
        CHECK(state IN ('active','stopped')),
    received_at TEXT NOT NULL,
    PRIMARY KEY(node_id,session_id)
);

CREATE INDEX IF NOT EXISTS ike_traffic_user_time
ON ike_traffic_sessions(user_id,observed_at);

CREATE INDEX IF NOT EXISTS ike_traffic_username_time
ON ike_traffic_sessions(username,observed_at);


CREATE TABLE IF NOT EXISTS ike_traffic_samples (
    event_id TEXT PRIMARY KEY,
    node_id TEXT NOT NULL
        CHECK(length(node_id) BETWEEN 1 AND 24 AND substr(node_id,1,1) GLOB '[a-z]' AND node_id NOT GLOB '*[^a-z0-9-]*'),
    session_id TEXT NOT NULL,
    user_id TEXT,
    username TEXT NOT NULL,
    kind TEXT NOT NULL
        CHECK(kind IN ('start','interim','stop')),
    observed_at TEXT NOT NULL,
    upload_bytes INTEGER NOT NULL
        CHECK(upload_bytes>=0),
    download_bytes INTEGER NOT NULL
        CHECK(download_bytes>=0),
    total_bytes INTEGER NOT NULL
        CHECK(total_bytes>=0),
    received_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ike_samples_session_time
ON ike_traffic_samples(
    node_id,
    session_id,
    observed_at
);

CREATE INDEX IF NOT EXISTS ike_samples_user_time
ON ike_traffic_samples(
    user_id,
    observed_at
);
"""

def connect(db):
    con=sqlite3.connect(db,timeout=30)
    con.row_factory=sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

def parse_time(value, field):
    if not isinstance(value,str) or len(value)>64:
        raise HTTPException(400,f"Invalid {field}")
    try:
        parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.astimezone(timezone.utc)
    except (ValueError,OverflowError):
        raise HTTPException(400,f"Invalid {field}") from None

def authenticate_node(con,node_id,token):
    if not isinstance(node_id,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,23}',node_id):
        raise HTTPException(401,"Unknown node")
    if not token:
        raise HTTPException(401,"Missing node credential")

    row=con.execute("""
        SELECT credential_hash
        FROM oc_node_credentials
        WHERE node_id=? AND revoked_at IS NULL
    """,(node_id,)).fetchone()

    if not row:
        raise HTTPException(401,"Unknown node")

    supplied=hashlib.sha256(token.encode("utf-8")).digest()

    if not hmac.compare_digest(supplied,row["credential_hash"]):
        raise HTTPException(401,"Invalid node credential")

def install(app,context):
    db=context["DB"]

    with connect(db) as con:
        con.executescript(SCHEMA)
        con.executescript(OC_LIVE_SCHEMA)

    @app.post("/oc/node/traffic")
    async def oc_node_traffic(request: Request):
        auth=request.headers.get("Authorization","")
        token=auth[7:].strip() if auth.startswith("Bearer ") else ""
        node_id=request.query_params.get("node","").strip()

        with connect(db) as con:
            authenticate_node(con,node_id,token)

        raw=await request.body()
        if len(raw)>256000:
            raise HTTPException(413,"Traffic batch too large")

        try:
            body=json.loads(raw)
        except (ValueError,UnicodeDecodeError):
            raise HTTPException(400,"Invalid JSON")

        if not isinstance(body,dict):
            raise HTTPException(400,"Invalid traffic batch")

        items=body.get("sessions")
        if not isinstance(items,list) or not 1<=len(items)<=1000:
            raise HTTPException(400,"Invalid sessions list")

        now=datetime.now(timezone.utc)
        validated=[]

        for item in items:
            if not isinstance(item,dict):
                raise HTTPException(400,"Invalid session")

            sid=item.get("sessionId")
            username=item.get("username")
            completion=item.get("completion")
            upload=item.get("uploadBytes")
            download=item.get("downloadBytes")

            if not isinstance(sid,str) or not SESSION_RE.fullmatch(sid):
                raise HTTPException(400,"Invalid session ID")

            if not isinstance(username,str) or not USERNAME_RE.fullmatch(username):
                raise HTTPException(400,"Invalid username")

            if completion not in COMPLETIONS:
                raise HTTPException(400,"Invalid completion type")

            if type(upload) is not int or type(download) is not int:
                raise HTTPException(400,"Invalid traffic counters")

            if upload<0 or download<0 or upload>2**63-1 or download>2**63-1:
                raise HTTPException(400,"Invalid traffic counters")

            connected=parse_time(item.get("connectedAt"),"connectedAt")
            disconnected=parse_time(item.get("disconnectedAt"),"disconnectedAt")

            if disconnected<connected:
                raise HTTPException(400,"Invalid session interval")

            if (disconnected-now).total_seconds()>300:
                raise HTTPException(400,"Timestamp is in the future")

            validated.append((
                sid,username,connected,disconnected,
                upload,download,completion
            ))

        stored=0

        with connect(db) as con:
            authenticate_node(con,node_id,token)

            for sid,username,connected,disconnected,upload,download,completion in validated:
                device=con.execute("""
                    SELECT id,user_id
                    FROM oc_devices
                    WHERE username=?
                """,(username,)).fetchone()

                if not device:
                    raise HTTPException(400,"Unknown AnyConnect device")

                total=upload+download

                cursor=con.execute("""
                    INSERT OR IGNORE INTO oc_traffic_sessions(
                        node_id,session_id,device_id,user_id,username,
                        connected_at,disconnected_at,
                        upload_bytes,download_bytes,total_bytes,
                        completion_type,received_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,(
                    node_id,sid,device["id"],device["user_id"],username,
                    connected.isoformat(),disconnected.isoformat(),
                    upload,download,total,completion,now.isoformat()
                ))

                stored+=cursor.rowcount

        return {
            "status":"ok",
            "node":node_id,
            "stored":stored,
            "received":len(validated),
        }


    @app.post("/ike/node/traffic")
    async def ike_node_traffic(request: Request):
        auth=request.headers.get("Authorization","")
        token=auth[7:].strip() if auth.startswith("Bearer ") else ""
        node_id=request.query_params.get("node","").strip()

        with connect(db) as con:
            authenticate_node(con,node_id,token)

        raw=await request.body()

        if len(raw)>256000:
            raise HTTPException(413,"Traffic batch too large")

        try:
            body=json.loads(raw)
        except (ValueError,UnicodeDecodeError):
            raise HTTPException(400,"Invalid JSON")

        if not isinstance(body,dict):
            raise HTTPException(400,"Invalid traffic batch")

        items=body.get("events")

        if not isinstance(items,list) or not 1<=len(items)<=1000:
            raise HTTPException(400,"Invalid events list")

        now=datetime.now(timezone.utc)
        validated=[]

        for item in items:
            if not isinstance(item,dict):
                raise HTTPException(400,"Invalid event")

            event_id=item.get("eventId")
            sid=item.get("sessionId")
            username=item.get("username")
            kind=item.get("kind")
            upload=item.get("upload")
            download=item.get("download")

            if (
                not isinstance(event_id,str)
                or not re.fullmatch(r"[0-9a-f]{64}",event_id)
            ):
                raise HTTPException(400,"Invalid event ID")

            if (
                not isinstance(sid,str)
                or not re.fullmatch(r"[0-9]{1,20}-[0-9]{1,20}",sid)
            ):
                raise HTTPException(400,"Invalid session ID")

            if (
                not isinstance(username,str)
                or not re.fullmatch(r"[A-Za-z0-9_.@-]{1,128}",username)
            ):
                raise HTTPException(400,"Invalid username")

            if kind not in {"start","interim","stop"}:
                raise HTTPException(400,"Invalid event kind")

            if (
                type(upload) is not int
                or type(download) is not int
                or upload<0
                or download<0
                or upload>2**63-1
                or download>2**63-1
            ):
                raise HTTPException(400,"Invalid traffic counters")

            observed=parse_time(
                item.get("observedAt"),
                "observedAt"
            )

            if (observed-now).total_seconds()>300:
                raise HTTPException(
                    400,
                    "Timestamp is in the future"
                )

            validated.append((
                event_id,
                sid,
                username,
                kind,
                observed,
                upload,
                download,
            ))

        with connect(db) as con:
            authenticate_node(con,node_id,token)

            for (
                event_id,
                sid,
                username,
                kind,
                observed,
                upload,
                download,
            ) in validated:

                # Map IKEv2 username to the authoritative TOLF account.
                from ike_traffic_owner import owner_for
                owner=owner_for(con,username,node_id)

                user_id=owner["user_id"] if owner else None
                stamp=observed.isoformat()
                total=upload+download

                existing=con.execute("""
                    SELECT username,upload_bytes,download_bytes
                    FROM ike_traffic_sessions
                    WHERE node_id=? AND session_id=?
                """,(node_id,sid)).fetchone()


                # Preserve every unique RADIUS accounting event.
                # Session counters remain cumulative in
                # ike_traffic_sessions; samples provide the
                # time series required for exact period usage.
                con.execute("""
                    INSERT OR IGNORE INTO ike_traffic_samples(
                        event_id,
                        node_id,
                        session_id,
                        user_id,
                        username,
                        kind,
                        observed_at,
                        upload_bytes,
                        download_bytes,
                        total_bytes,
                        received_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,(
                    event_id,
                    node_id,
                    sid,
                    user_id,
                    username,
                    kind,
                    stamp,
                    upload,
                    download,
                    total,
                    now.isoformat(),
                ))

                if existing:
                    if existing["username"] != username:
                        raise HTTPException(
                            409,
                            "IKE session identity changed"
                        )

                    # RADIUS interim counters are cumulative.
                    # Never allow an older/smaller update to reduce usage.
                    upload=max(upload,existing["upload_bytes"])
                    download=max(
                        download,
                        existing["download_bytes"]
                    )
                    total=upload+download

                    con.execute("""
                        UPDATE ike_traffic_sessions
                        SET
                            user_id=COALESCE(user_id,?),
                            observed_at=?,
                            stopped_at=CASE
                                WHEN ?='stop' THEN ?
                                ELSE stopped_at
                            END,
                            upload_bytes=?,
                            download_bytes=?,
                            total_bytes=?,
                            state=CASE
                                WHEN ?='stop' THEN 'stopped'
                                ELSE state
                            END,
                            received_at=?
                        WHERE node_id=? AND session_id=?
                    """,(
                        user_id,
                        stamp,
                        kind,
                        stamp,
                        upload,
                        download,
                        total,
                        kind,
                        now.isoformat(),
                        node_id,
                        sid,
                    ))

                else:
                    con.execute("""
                        INSERT INTO ike_traffic_sessions(
                            node_id,
                            session_id,
                            user_id,
                            username,
                            started_at,
                            observed_at,
                            stopped_at,
                            upload_bytes,
                            download_bytes,
                            total_bytes,
                            state,
                            received_at
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """,(
                        node_id,
                        sid,
                        user_id,
                        username,
                        stamp,
                        stamp,
                        stamp if kind=="stop" else None,
                        upload,
                        download,
                        total,
                        "stopped" if kind=="stop" else "active",
                        now.isoformat(),
                    ))

        return {
            "status":"ok",
            "node":node_id,
            "received":len(validated),
        }



    @app.get("/admin/vpn-status")
    def admin_vpn_status(
        request: Request,
        period: str = "24h",
    ):
        admin_id=context["authenticated_user_id"](request)

        seconds={
            "24h":24*60*60,
            "7d":7*24*60*60,
            "30d":30*24*60*60,
        }.get(period)

        if seconds is None:
            raise HTTPException(
                400,
                "invalid_period",
            )

        now=datetime.now(timezone.utc)
        start_dt=datetime.fromtimestamp(
            now.timestamp()-seconds,
            timezone.utc,
        )
        start=start_dt.isoformat()

        # An active IKE session must have reported recently.
        online_cutoff=datetime.fromtimestamp(
            now.timestamp()-180,
            timezone.utc,
        ).isoformat()

        with connect(db) as con:
            if not con.execute(
                """
                SELECT 1
                FROM admin_roles
                WHERE user_id=?
                """,
                (admin_id,),
            ).fetchone():
                raise HTTPException(
                    403,
                    "administrator_required",
                )

            registry=con.execute("""
                SELECT
                    number,
                    account_id,
                    vpn_username,
                    vpn_active
                FROM managed_users
                WHERE deleted_at IS NULL
                ORDER BY number
            """).fetchall()

            # Intermediate and final AnyConnect counters share one session.
            oc_usage={
                uid:{"sessions":row["sessions"],"bytes":row["total"]}
                for uid,row in oc_live_usage(con,start).items()
            }

            # Exact IKEv2 delta traffic from sample history.
            samples=con.execute("""
                SELECT
                    event_id,
                    node_id,
                    session_id,
                    user_id,
                    observed_at,
                    upload_bytes,
                    download_bytes
                FROM ike_traffic_samples
                WHERE user_id IS NOT NULL
                ORDER BY
                    node_id,
                    session_id,
                    observed_at,
                    event_id
            """).fetchall()

            previous={}
            ike_usage={}

            for sample in samples:
                key=(
                    sample["node_id"],
                    sample["session_id"],
                )

                current=(
                    int(sample["upload_bytes"]),
                    int(sample["download_bytes"]),
                )

                prev=previous.get(key)
                previous[key]=current

                if prev is None:
                    continue

                try:
                    observed=datetime.fromisoformat(
                        sample["observed_at"].replace(
                            "Z",
                            "+00:00",
                        )
                    )
                except (
                    ValueError,
                    AttributeError,
                ):
                    continue

                if observed < start_dt:
                    continue

                delta=(
                    max(0,current[0]-prev[0])
                    +
                    max(0,current[1]-prev[1])
                )

                usage=ike_usage.setdefault(
                    sample["user_id"],
                    {
                        "sessions":set(),
                        "bytes":0,
                    },
                )

                if delta > 0:
                    usage["sessions"].add(key)
                    usage["bytes"] += delta

            # Live IKE state. Fresh interim is required so a
            # missing Stop packet cannot leave a user online forever.
            ike_online={}

            for row in con.execute("""
                SELECT
                    user_id,
                    node_id
                FROM ike_traffic_sessions
                WHERE user_id IS NOT NULL
                  AND state='active'
                  AND observed_at>=?
                GROUP BY user_id,node_id
            """,(online_cutoff,)):
                ike_online.setdefault(
                    row["user_id"],
                    [],
                ).append(row["node_id"])

            # One bounded, fresh snapshot for every device. Do not perform
            # sequential SSH/controller requests inside a traffic page request.
            from tolf_admin import SESSION_NODES, query_sessions_node
            snapshots=[query_sessions_node(node) for node in SESSION_NODES]
            complete=all(
                item.get("status")=="ok" and any(
                    p.get("protocol")=="AnyConnect" and p.get("status")=="ok"
                    for p in item.get("protocolStatus",[])
                ) for item in snapshots
            )
            devices={row["username"]:row["user_id"] for row in con.execute(
                "SELECT user_id,username FROM oc_devices"
            )}
            oc_live={}
            for item in snapshots:
                if item.get("status")!="ok":
                    continue
                for session in item.get("sessions",[]):
                    if session.get("protocol")!="AnyConnect":
                        continue
                    uid=devices.get(session.get("identity"))
                    if not uid:
                        continue
                    live=oc_live.setdefault(uid,{
                        "connected":False,"nodes":set(),"complete":complete,
                    })
                    live["connected"]=True
                    live["nodes"].add(item["node"])

            users=[]

            for row in registry:
                user_id=row["account_id"]

                oc=oc_usage.get(
                    user_id,
                    {
                        "sessions":0,
                        "bytes":0,
                    },
                )

                ike=ike_usage.get(
                    user_id,
                    {
                        "sessions":set(),
                        "bytes":0,
                    },
                )

                nodes=sorted(
                    set(
                        ike_online.get(
                            user_id,
                            [],
                        )
                    )
                )

                oc_state=oc_live.get(
                    user_id,
                    {
                        "connected":False,
                        "nodes":set(),
                        "complete":complete,
                    },
                )

                oc_nodes=sorted(
                    oc_state["nodes"]
                )

                anyconnect_online=bool(
                    oc_state["connected"]
                )

                ikev2_online=bool(nodes)

                users.append({
                    "number":row["number"],
                    "userId":user_id,
                    "username":row["vpn_username"],
                    "accessActive":bool(
                        row["vpn_active"]
                    ),
                    "connections":{
                        "ikev2":ikev2_online,
                        "ikev2Nodes":nodes,
                        "anyconnect":
                            anyconnect_online,
                        "anyconnectNodes":
                            oc_nodes,
                        "anyconnectComplete":
                            bool(
                                oc_state[
                                    "complete"
                                ]
                            ),
                    },
                    "online":(
                        ikev2_online
                        or anyconnect_online
                    ),
                    "traffic":{
                        "anyconnectSessions":
                            oc["sessions"],
                        "anyconnectBytes":
                            oc["bytes"],
                        "ikev2Sessions":
                            len(ike["sessions"]),
                        "ikev2Bytes":
                            ike["bytes"],
                        "totalBytes":
                            oc["bytes"]+ike["bytes"],
                    },
                })

        return {
            "status":"ok",
            "period":period,
            "from":start,
            "observedAt":now.isoformat(),
            "users":users,
        }


    @app.get("/admin/traffic")
    def admin_traffic(request: Request, period: str = "30d"):
        user_id=context["authenticated_user_id"](request)
        seconds={"24h":86400,"7d":604800,"30d":2592000}.get(period)
        if seconds is None:
            raise HTTPException(400,"invalid_period")
        now=datetime.now(timezone.utc)
        start=datetime.fromtimestamp(now.timestamp()-seconds,timezone.utc).isoformat()
        with connect(db) as con:
            if not con.execute("SELECT 1 FROM admin_roles WHERE user_id=?",(user_id,)).fetchone():
                raise HTTPException(403,"administrator_required")
            totals=oc_live_usage(con,start)
            users=[]
            for uid,row in sorted(totals.items(),key=lambda item:(-item[1]["total"],item[0])):
                number=con.execute("SELECT MIN(number) FROM managed_users WHERE account_id=? AND deleted_at IS NULL",(uid,)).fetchone()[0]
                users.append({
                    "userId":uid,"number":number,"sessions":row["sessions"],
                    "uploadBytes":row["upload"],"downloadBytes":row["download"],
                    "totalBytes":row["total"],"recoveredSessions":row["recovered"],
                    "nodes":[row["nodes"][n] for n in sorted(row["nodes"])],
                })
        return {"status":"ok","period":period,"from":start,"observedAt":now.isoformat(),
                "users":users,"totalBytes":sum(x["totalBytes"] for x in users)}
