"""Traffic request regression: no per-device controller calls."""
import importlib.util
import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI
import tolf_admin
from tolf_oc_live import SCHEMA as LIVE_SCHEMA

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("traffic_candidate",ROOT/"setup/admin/tolf_oc_traffic.py")
traffic=importlib.util.module_from_spec(spec)
spec.loader.exec_module(traffic)


def test_shared_snapshot_keeps_usage_and_period(tmp_path,monkeypatch):
    db=tmp_path/"db"
    with sqlite3.connect(db) as con:
        con.executescript("""
CREATE TABLE admin_roles(user_id TEXT);
INSERT INTO admin_roles VALUES('admin');
CREATE TABLE managed_users(number INTEGER,account_id TEXT,vpn_username TEXT,vpn_active INTEGER,deleted_at TEXT);
INSERT INTO managed_users VALUES(16,'owner','user0',1,NULL);
CREATE TABLE oc_devices(user_id TEXT,username TEXT,state TEXT,expires_at TEXT);
INSERT INTO oc_devices VALUES('owner','oc-one','active','2099-01-01');
INSERT INTO oc_devices VALUES('owner','oc-two','active','2099-01-01');
""")
    monkeypatch.setattr(traffic,"oc_live_usage",lambda con,start:{"owner":{"sessions":3,"total":900}})
    calls=[]
    def snapshot(node):
        calls.append(node)
        return {"node":node,"status":"ok","protocolStatus":[{"protocol":"AnyConnect","status":"ok"}],
                "sessions":[{"protocol":"AnyConnect","identity":"oc-one"}] if node=="moscow" else []}
    monkeypatch.setattr(tolf_admin,"query_sessions_node",snapshot)
    def forbidden(*args):
        raise AssertionError("Per-device controller must not be called")
    app=FastAPI()
    traffic.install(app,{"DB":str(db),"authenticated_user_id":lambda req:"admin","oc_session_status":forbidden})
    endpoint=next(r.endpoint for r in app.routes if getattr(r,"path",None)=="/admin/vpn-status")
    for period,seconds in (("24h",86400),("7d",604800),("30d",2592000)):
        calls.clear()
        result=endpoint(None,period)
        from datetime import datetime
        duration=datetime.fromisoformat(result["observedAt"])-datetime.fromisoformat(result["from"])
        assert duration.total_seconds()==seconds
        assert calls==list(tolf_admin.SESSION_NODES)
        user=result["users"][0]
        assert user["traffic"]["totalBytes"]==900
        assert user["connections"]["anyconnectNodes"]==["moscow"]
    monkeypatch.setattr(tolf_admin,"query_sessions_node",lambda node:{"node":node,"status":"error"})
    result=endpoint(None,"24h")
    assert result["users"][0]["traffic"]["totalBytes"]==900
    assert result["users"][0]["connections"]["anyconnectComplete"] is False
