#!/usr/bin/env python3
"""London: preserve the existing registry number when adopting a VPN user."""
import ast
import sys
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import urllib.request
import json
HELPER = "\ndef reconcile_managed_user(con, user_id, username):\n    # Called only after Riga verified ownership, inside the vpn_access transaction.\n    if not con.execute(\"SELECT 1 FROM sqlite_master WHERE type='table' AND name='managed_users'\").fetchone():\n        return\n    original = con.execute(\n        \"SELECT number,account_id,source,deleted_at FROM managed_users WHERE vpn_username=?\",\n        (username,)).fetchone()\n    current = con.execute(\n        \"SELECT number,vpn_username,vpn_active,deleted_at FROM managed_users WHERE account_id=?\",\n        (user_id,)).fetchone()\n    if not original or original[1] == user_id:\n        return\n    if original[1] is not None or original[2] not in ('legacy', 'manual') or original[3] is not None:\n        raise HTTPException(409, 'already_linked')\n    if not current or current[1] is not None or current[2] != 0 or current[3] is not None:\n        raise HTTPException(409, 'account_has_vpn')\n    # Retain the provisional row and its number as an archived audit record.\n    con.execute(\"UPDATE managed_users SET account_id=NULL,deleted_at=? WHERE number=?\",\n                (CTX['utc_iso'](CTX['utc_now']()), current[0]))\n    con.execute(\"UPDATE managed_users SET account_id=? WHERE number=?\", (user_id, original[0]))\n\n"

def patch(source):
    if "# TOLF managed registry adoption v1" in source:
        return source
    anchor = "        with connect() as con:\n            con.execute('INSERT INTO vpn_access(user_id,vpn_username,created_at,server) VALUES(?,?,?,?)',"
    if source.count(anchor) != 1:
        raise RuntimeError("Unexpected invitation handler; nothing changed")
    replacement = "        with connect() as con:\n            con.execute('BEGIN IMMEDIATE')\n            reconcile_managed_user(con, user_id, value['username'])\n            con.execute('INSERT INTO vpn_access(user_id,vpn_username,created_at,server) VALUES(?,?,?,?)',"
    result = source.replace(anchor, replacement) + "\n# TOLF managed registry adoption v1\n" + HELPER
    compile(result, "tolf_invitations.py", "exec")
    return result

def patch_riga(source):
    old = "if (not owner or proof) and expires <= time.time():"
    new = "if not owner and expires <= time.time():"
    if new in source and old not in source:
        return source
    if source.count(old) != 1:
        raise RuntimeError("Unexpected Riga invitation helper; nothing changed")
    result = source.replace(old, new)
    compile(result, "tolf-invite", "exec")
    return result

def main():
    if os.geteuid() != 0:
        raise SystemExit("Run on London as root")
    role = sys.argv[1] if len(sys.argv) == 2 else ""
    if role not in ("riga", "london"):
        raise SystemExit("Specify riga or london")
    lock = open("/var/lock/tolf-provision.lock" if role == "riga" else "/var/lock/tolf-invitations-install.lock", "a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    target = Path("/usr/local/sbin/tolf-invite" if role == "riga" else "/opt/tolf-api/tolf_invitations.py")
    original = target.read_text()
    updated = patch_riga(original) if role == "riga" else patch(original)
    if updated == original:
        print("OK: registry adoption fix already installed")
        return
    backup = Path(tempfile.mkdtemp(prefix="tolf-registry-adoption-backup-", dir="/root"))
    shutil.copy2(target, backup / target.name)
    print("Backup:", backup, flush=True)
    info = target.stat()
    def write(content):
        fd, name = tempfile.mkstemp(dir=target.parent, prefix=".tolf-registry-")
        try:
            with os.fdopen(fd, "w") as out:
                os.fchmod(out.fileno(), info.st_mode & 0o777)
                os.fchown(out.fileno(), info.st_uid, info.st_gid)
                out.write(content)
                out.flush()
                os.fsync(out.fileno())
            os.replace(name, target)
        finally:
            if os.path.exists(name): os.unlink(name)
    try:
        write(updated)
        if role == "riga":
            print("OK: same-account invitation retries fixed on riga")
            return
        subprocess.run(["systemctl","restart","tolf-api.service"],check=True,timeout=40)
        for attempt in range(10):
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/vpn/invitations/capabilities",timeout=3) as response:
                    assert json.load(response).get("version") == 2
                break
            except Exception:
                if attempt == 9: raise
                time.sleep(1)
    except Exception:
        write(original)
        if role == "london":
            subprocess.run(["systemctl","restart","tolf-api.service"],check=False,timeout=40)
        raise
    print("OK: registry adoption fix installed on london; retry VPN linking")
if __name__ == "__main__":
    main()
