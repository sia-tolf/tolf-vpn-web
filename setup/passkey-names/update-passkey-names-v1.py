#!/usr/bin/env python3
"""Install meaningful Passkey labels on the London API only."""
import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
MODULE = "\"\"\"Human-readable Passkey labels. Credentials and user handles stay unchanged.\"\"\"\nimport base64\nimport re\nimport sqlite3\nimport unicodedata\nfrom fastapi import HTTPException, Request\n\ndef label(payload):\n    value = (payload or {}).get(\"passkeyName\")\n    if not isinstance(value, str):\n        raise HTTPException(400, \"Enter a Passkey name\")\n    value = value.strip()\n    if value.startswith(\"TOLF · \"):\n        value = value[7:].strip()\n    if not value or len(value) > 80 or any(unicodedata.category(c).startswith(\"C\") for c in value):\n        raise HTTPException(400, \"Passkey name must contain 1–80 visible characters\")\n    return \"TOLF · \" + value\n\ndef install(app, ns):\n    @app.get(\"/passkeys/naming\")\n    def naming():\n        return {\"status\": \"ok\", \"version\": 1}\n\n    @app.post(\"/passkeys/rename\")\n    def rename(request: Request, payload: dict):\n        if request.headers.get(\"origin\") != ns[\"ORIGIN\"]:\n            raise HTTPException(403, \"Invalid origin\")\n        user_id = ns[\"authenticated_user_id\"](request)\n        name = label(payload)\n        encoded = payload.get(\"id\")\n        if not isinstance(encoded, str) or not re.fullmatch(r\"[A-Za-z0-9_-]{1,2048}\", encoded):\n            raise HTTPException(400, \"Invalid Passkey ID\")\n        try:\n            credential_id = base64.urlsafe_b64decode(encoded + \"=\" * (-len(encoded) % 4))\n        except ValueError:\n            raise HTTPException(400, \"Invalid Passkey ID\")\n        if base64.urlsafe_b64encode(credential_id).rstrip(b\"=\").decode() != encoded:\n            raise HTTPException(400, \"Invalid Passkey ID\")\n        with ns[\"tolf_promos\"].account_operation(ns[\"DB\"], user_id):\n            with sqlite3.connect(ns[\"DB\"]) as con:\n                changed = con.execute(\"UPDATE passkeys SET name=? WHERE credential_id=? AND user_id=?\",\n                                      (name, credential_id, user_id))\n                if changed.rowcount != 1:\n                    raise HTTPException(404, \"Passkey not found\")\n        return {\"status\": \"ok\", \"passkeyName\": name}\n"

def patch(source):
    if "# TOLF Passkey names v1" in source:
        return source
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    replacements = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name == "passkey_register_begin":
            old = "".join(lines[node.lineno-1:node.end_lineno])
            assert 'passkey_name = "TOLF Passkey #1"' in old, "Unexpected registration handler"
            new = old.replace("def passkey_register_begin():", "def passkey_register_begin(payload: dict | None = None):", 1)
            new = new.replace('passkey_name = "TOLF Passkey #1"', "passkey_name = tolf_passkey_names.label(payload)", 1)
            assert new != old
            replacements.append((node.lineno-1, node.end_lineno, new))
        elif node.name == "passkeys_add_begin":
            old = "".join(lines[node.lineno-1:node.end_lineno])
            start = old.index('        rows = con.execute("SELECT name FROM passkeys')
            end = old.index("\n    finally:", start)
            new = old[:start] + "        passkey_name = tolf_passkey_names.label(payload)" + old[end:]
            new = new.replace("def passkeys_add_begin(request: Request):", "def passkeys_add_begin(request: Request, payload: dict | None = None):", 1)
            assert "payload: dict" in new
            replacements.append((node.lineno-1, node.end_lineno, new))
    assert len(replacements) == 2, "Expected both registration handlers"
    for start, end, replacement in sorted(replacements, reverse=True):
        lines[start:end] = [replacement]
    result = "".join(lines) + "\n# TOLF Passkey names v1\nimport tolf_passkey_names\ntolf_passkey_names.install(app, globals())\n"
    compile(result, "main.py", "exec")
    return result

def main():
    if sys.argv[1:] != ["london"] or os.geteuid() != 0:
        raise SystemExit("Run as root: python3 update-passkey-names-v1.py london")
    root = Path("/opt/tolf-api")
    main_file = root / "main.py"
    replacement = patch(main_file.read_text())
    compile(MODULE, "tolf_passkey_names.py", "exec")
    backup = Path(tempfile.mkdtemp(prefix="tolf-passkey-names-backup-", dir="/root"))
    targets = {main_file: replacement, root / "tolf_passkey_names.py": MODULE}
    existed = {}
    for target in targets:
        existed[target] = target.exists()
        if target.exists():
            shutil.copy2(target, backup / target.name)
    print("Backup:", backup, flush=True)
    def write(target, content):
        fd, temporary = tempfile.mkstemp(dir=root, prefix=".passkey-names-")
        try:
            with os.fdopen(fd, "w") as out:
                out.write(content)
                out.flush()
                os.fsync(out.fileno())
            owner = main_file.stat()
            os.chown(temporary, owner.st_uid, owner.st_gid)
            os.chmod(temporary, owner.st_mode & 0o777)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    try:
        for target, content in targets.items():
            write(target, content)
        subprocess.run(["systemctl", "restart", "tolf-api.service"], check=True, timeout=40)
        import time
        time.sleep(2)
        subprocess.run(["systemctl", "is-active", "--quiet", "tolf-api.service"], check=True)
    except Exception:
        for target in targets:
            if existed[target]:
                shutil.copy2(backup / target.name, target)
            else:
                target.unlink(missing_ok=True)
        subprocess.run(["systemctl", "restart", "tolf-api.service"], check=False, timeout=40)
        raise
    print("OK: meaningful Passkey names installed on london")
if __name__ == "__main__":
    main()
