#!/usr/bin/env python3
"""Add ordered routing groups to an existing UK delivery installation."""
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path("/opt/tolf-api")
DB = Path("/var/lib/tolf-api/tolf.db")
OLD_HASH = "c3d90f60b064b5fa816dd81f78a639d88fc59dc882f67e0d458ae7b0e22ebbd3"


def atomic(path, data, info):
    fd, name = tempfile.mkstemp(prefix=".routing-groups-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, info.st_mode & 0o777)
        os.chown(name, info.st_uid, info.st_gid)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def health():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(15):
        try:
            with opener.open("http://127.0.0.1:8000/health", timeout=2) as reply:
                if reply.status != 200:
                    raise RuntimeError("API health failed")
            try:
                opener.open("http://127.0.0.1:8000/vpn/routing-rules", timeout=2)
            except urllib.error.HTTPError as error:
                if error.code == 401:
                    return
        except (OSError, RuntimeError):
            pass
        time.sleep(1)
    raise RuntimeError("API health/authentication check failed")


def main():
    if os.geteuid() != 0 or socket.gethostname().split(".")[0] != "EDISUK":
        raise RuntimeError("Run as root on EDISUK only")
    target = ROOT / "tolf_personal_routing.py"
    source = Path(__file__).resolve().with_name("tolf_personal_routing.py")
    if target.is_symlink() or not DB.is_file():
        raise RuntimeError("Unexpected installation")
    before = target.read_bytes()
    after = source.read_bytes()
    if before == after:
        health()
        print("OK: routing groups already installed.")
        return
    if hashlib.sha256(before).hexdigest() != OLD_HASH:
        raise RuntimeError("Installed API differs from the expected version; no changes made")
    compile(after, str(source), "exec")
    subprocess.run(["systemctl", "is-active", "--quiet", "tolf-api"], check=True)
    health()
    backup = Path(tempfile.mkdtemp(prefix="routing-groups-backup-", dir=ROOT))
    shutil.copy2(target, backup / target.name)
    # Keep a consistent backup, but rollback never overwrites the live database.
    with sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True) as con:
        con.execute("SELECT rules_json, revision FROM vpn_personal_routing LIMIT 0")
        with sqlite3.connect(backup / "tolf.db") as dest:
            con.backup(dest)
    print("Backup:", backup, flush=True)
    info = target.stat()
    if target.read_bytes() != before:
        raise RuntimeError("API changed during preparation; installation cancelled")
    sys.path.insert(0, str(ROOT))
    try:
        spec = importlib.util.spec_from_file_location("routing_groups_check", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.initialize(str(DB))
        with module.connect(str(DB)) as con:
            for row in con.execute("SELECT * FROM vpn_personal_routing"):
                state = module.snapshot(row)
                module.validate_groups(state["routingGroups"], state["routingRules"])
        atomic(target, after, info)
        subprocess.run(["systemctl", "restart", "tolf-api"], check=True, timeout=30)
        health()
    except Exception:
        atomic(target, before, info)
        subprocess.run(["systemctl", "restart", "tolf-api"], check=True, timeout=30)
        health()
        print("Code restored. Existing rules and the additive groups column retained.", flush=True)
        raise
    print("OK: account routing groups enabled; existing rules preserved.")
    print("Rollback: cp -p " + str(backup / target.name) + " " + str(target)
          + " && systemctl restart tolf-api")


if __name__ == "__main__":
    main()
