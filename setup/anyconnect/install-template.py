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
import socket
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
    if sys.argv[1:] not in ([], ["--activate"], ['--activate-riga']):
        raise RuntimeError("Usage: install.py [--activate|--activate-riga]")
    riga = sys.argv[1:] == ['--activate-riga']
    activate = sys.argv[1:] == ["--activate"]
    if socket.gethostname().split('.')[0] != 'EDISUK':
        raise RuntimeError('This installer must run on EDISUK')
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
        if name not in {"tolf_oc_certificates.py", "tolf_anyconnect.py", 'tolf_oc_nodes.py'}:
            raise RuntimeError("Unexpected installer payload")
        data = base64.b64decode(entry["data"], validate=True)
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise RuntimeError("Installer payload hash mismatch")
        compile(data, name, "exec")
        modules[name] = data
    if len(modules) != 3:
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
    gate = directory / "activation.json"
    old_gate = gate.read_bytes() if gate.exists() else None
    restarted = False
    stopped = False
    if riga and old_gate is None:
        raise RuntimeError('Activate Moscow before adding Riga')
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
        if activate:
            run("runuser", "-u", user, "--", str(PYTHON), "-c",
                "import sys; sys.path.insert(0,sys.argv[1]); from tolf_anyconnect import Node; "
                "assert Node(sys.argv[2]).health(fresh=True), 'Moscow node verification failed'",
                str(API), fingerprint)
            atomic_write(gate, json.dumps({"enabled": True, "caSha256": fingerprint}).encode(), 0o600)
            os.chown(gate, owner.pw_uid, owner.pw_gid)
        if riga:
            if json.loads(old_gate) not in (
                    {'enabled': True, 'caSha256': fingerprint},
                    {'enabled': True, 'caSha256': fingerprint, 'nodes': ['moscow', 'riga']}):
                raise RuntimeError('Existing activation gate does not match this CA')
            # Public CRL downloads require the existing API to remain available.
            run('runuser', '-u', user, '--', str(PYTHON), '-c',
                'import sys; sys.path.insert(0,sys.argv[1]); from tolf_anyconnect import configured_nodes; '
                'n=configured_nodes(sys.argv[2],["moscow","riga"]); '
                'assert n.health(fresh=True), "Node verification failed"; '
                '[node.sync_crl() for node in n.nodes.values()]', str(API), fingerprint)
            stopped = True
            subprocess.run(['systemctl', 'stop', 'tolf-api'], check=True)
            # Freeze writes while registering the stored acknowledged policies.
            run('runuser', '-u', user, '--', str(PYTHON), '-c',
                'import sys,sqlite3,datetime; sys.path.insert(0,sys.argv[1]); '
                'from tolf_anyconnect import configured_nodes; '
                'n=configured_nodes(sys.argv[2],["moscow","riga"]); '
                'con=sqlite3.connect(sys.argv[3]); '
                'rows=con.execute("SELECT username,mode FROM oc_devices WHERE state=\'active\' AND expires_at>? '
                'AND EXISTS (SELECT 1 FROM users WHERE id=oc_devices.user_id)",'
                '(datetime.datetime.now(datetime.timezone.utc).isoformat(),)).fetchall(); '
                '[n.nodes["riga"].set(username,mode) for username,mode in rows]; '
                'print("Riga registered devices:",len(rows))', str(API), fingerprint, str(db))
            atomic_write(gate, json.dumps({'enabled': True, 'caSha256': fingerprint,
                                          'nodes': ['moscow', 'riga']}).encode(), 0o600)
            os.chown(gate, owner.pw_uid, owner.pw_gid)
        expected_enabled = gate.exists() and json.loads(gate.read_text()) in (
            {"enabled": True, "caSha256": fingerprint},
            {"enabled": True, "caSha256": fingerprint, 'nodes': ['moscow', 'riga']})
        atomic_write(API / "main.py", updated.encode())
        restarted = True
        subprocess.run(["systemctl", "restart", "tolf-api"], check=True)
        result = None
        for _ in range(20):
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/oc/access/capabilities", timeout=30) as response:
                    result = json.load(response)
                if result.get("version") == 2 and result.get("guestSetup") is True and result.get("caSha256") == fingerprint:
                    break
            except (OSError, ValueError):
                pass
            time.sleep(1)
        if (not result or result.get("version") != 2 or result.get("guestSetup") is not True or result.get("caSha256") != fingerprint
                or result.get("issuance") is not expected_enabled or result.get("nodeReady") is not expected_enabled):
            raise RuntimeError("AnyConnect API health check failed")
        if riga and [item['id'] for item in result.get('ingresses', [])] != ['moscow', 'riga']:
            raise RuntimeError('Riga activation was not acknowledged by the API')
        run(str(PYTHON), "-c",
            "import sys,urllib.request; sys.path.insert(0,sys.argv[1]); "
            "from cryptography import x509; from tolf_oc_certificates import Authority; "
            "a=Authority(sys.argv[2]); "
            "c=x509.load_pem_x509_crl(urllib.request.urlopen('http://127.0.0.1:8000/oc/access/crl.pem',timeout=10).read()); "
            "assert c.issuer==a.cert.subject and c.is_signature_valid(a.cert.public_key()); "
            "print('CRL signature: OK')",
            str(API), str(directory))
    except Exception:
        if old_gate is None:
            gate.unlink(missing_ok=True)
        else:
            atomic_write(gate, old_gate, 0o600)
            os.chown(gate, owner.pw_uid, owner.pw_gid)
        atomic_write(API / "main.py", (backup / "main.py").read_bytes())
        for name in modules:
            if (backup / name).exists():
                atomic_write(API / name, (backup / name).read_bytes())
            else:
                (API / name).unlink(missing_ok=True)
        if restarted or stopped:
            subprocess.run(["systemctl", "restart", "tolf-api"], check=False)
        print("Existing API restored. Backup:", backup, file=sys.stderr)
        print("The new CA, if created, is preserved for a retry.", file=sys.stderr)
        raise
    print("OK: UK AnyConnect certificate foundation installed.")
    print("CA SHA256:", fingerprint)
    print("Backup:", backup)
    print("Device issuance:", "enabled" if expected_enabled else "disabled until Moscow node activation")
    print("Signed CRL endpoint: /oc/access/crl.pem")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
