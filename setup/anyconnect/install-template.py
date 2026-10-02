#!/usr/bin/env python3
"""Install UK AnyConnect foundation. Built with embedded, hash-checked modules."""
import ast
import base64
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

PAYLOAD = {}  # BUILD_PAYLOAD
API = Path("/opt/tolf-api")
PYTHON = API / "venv/bin/python"
MARKER = "# TOLF AnyConnect UK foundation v1"


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def atomic_write(path, data, mode=0o644):
    fd, temporary = tempfile.mkstemp(prefix=".oc-install-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    if os.geteuid() != 0:
        raise RuntimeError("Run this installer as root on EDISUK")
    source = (API / "main.py").read_text()
    tree = ast.parse(source)
    db = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DB" for t in node.targets):
            db = Path(ast.literal_eval(node.value))
    if db is None or not db.is_file():
        raise RuntimeError("Existing TOLF database was not found")
    if not PYTHON.is_file():
        raise RuntimeError("TOLF API Python environment was not found")
    run(str(PYTHON), "-c", "import cryptography, fastapi")
    user = run("systemctl", "show", "tolf-api", "-p", "User", "--value") or "root"
    owner = pwd.getpwnam(user)
    modules = {}
    for name, entry in PAYLOAD.items():
        if name not in {"tolf_oc_certificates.py", "tolf_anyconnect.py"}:
            raise RuntimeError("Unexpected installer payload")
        data = base64.b64decode(entry["data"], validate=True)
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise RuntimeError("Installer payload hash mismatch")
        compile(data, name, "exec")
        modules[name] = data
    if len(modules) != 2:
        raise RuntimeError("Installer payload is incomplete")
    if MARKER not in source and "tolf_anyconnect.install" in source:
        raise RuntimeError("An unrecognized AnyConnect module is already installed")
    updated = source if MARKER in source else source.rstrip() + (
        "\n\n" + MARKER + "\nimport tolf_anyconnect\ntolf_anyconnect.install(app, globals())\n"
    )
    compile(updated, str(API / "main.py"), "exec")
    backup = Path(tempfile.mkdtemp(prefix="anyconnect-backup-", dir=API))
    shutil.copy2(API / "main.py", backup / "main.py")
    for name in modules:
        if (API / name).exists():
            shutil.copy2(API / name, backup / name)
    directory = db.parent / "anyconnect"
    if directory.is_symlink():
        raise RuntimeError("AnyConnect authority directory cannot be a symlink")
    restarted = False
    try:
        for name, data in modules.items():
            atomic_write(API / name, data)
        env = dict(os.environ, PYTHONPATH=str(API))
        fingerprint = subprocess.check_output(
            [str(PYTHON), "-c", "import sys; from tolf_oc_certificates import initialize; print(initialize(sys.argv[1]))",
             str(directory)], env=env, text=True).strip()
        os.chown(directory, owner.pw_uid, owner.pw_gid)
        os.chmod(directory, 0o700)
        for path in directory.iterdir():
            if path.is_symlink() or not path.is_file():
                raise RuntimeError("Unexpected file in AnyConnect authority directory")
            os.chown(path, owner.pw_uid, owner.pw_gid)
            os.chmod(path, 0o600)
        # Confirm that the actual service user can read and decrypt the CA.
        run("runuser", "-u", user, "--", str(PYTHON), "-c",
            "import sys; sys.path.insert(0,sys.argv[1]); from tolf_oc_certificates import Authority; Authority(sys.argv[2])",
            str(API), str(directory))
        atomic_write(API / "main.py", updated.encode())
        restarted = True
        subprocess.run(["systemctl", "restart", "tolf-api"], check=True)
        result = None
        for _ in range(20):
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/oc/access/capabilities", timeout=2) as response:
                    result = json.load(response)
                if result.get("version") == 1 and result.get("caSha256") == fingerprint:
                    break
            except (OSError, ValueError):
                pass
            time.sleep(1)
        if (not result or result.get("version") != 1 or result.get("caSha256") != fingerprint
                or result.get("issuance") is not False or result.get("nodeReady") is not False):
            raise RuntimeError("AnyConnect API health check failed")
    except Exception:
        atomic_write(API / "main.py", (backup / "main.py").read_bytes())
        for name in modules:
            if (backup / name).exists():
                atomic_write(API / name, (backup / name).read_bytes())
        if restarted:
            subprocess.run(["systemctl", "restart", "tolf-api"], check=False)
        print("Existing API restored. Backup:", backup, file=sys.stderr)
        print("The new CA, if created, is preserved for a retry.", file=sys.stderr)
        raise
    print("OK: UK AnyConnect certificate foundation installed.")
    print("CA SHA256:", fingerprint)
    print("Backup:", backup)
    print("Device issuance: disabled until Moscow node activation.")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
