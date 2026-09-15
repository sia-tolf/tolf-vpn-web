#!/usr/bin/env python3
"""Install quick setup on EDISUK without replacing unrelated API functionality."""
import ast
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
import zlib

PAYLOAD = ''
MARKER = '# TOLF quick setup v1'
PUBLIC_REQUESTED_SERVER = '''def requested_server(user_id, payload):
    server = (payload or {}).get("server", "riga")
    if server not in ("riga", "moscow"):
        raise HTTPException(400, "VPN server is not available")
    return server
'''


def patch(source):
    if MARKER in source:
        return source
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    replacements = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        old = ''.join(lines[node.lineno-1:node.end_lineno])
        if node.name == 'requested_server':
            public_variant = ast.dump(node) == ast.dump(ast.parse(PUBLIC_REQUESTED_SERVER).body[0])
            if old.count('return server') != 1 or (not public_variant and 'tolf_promos.allowed_servers(DB, user_id)' not in old):
                raise RuntimeError('Unrecognized requested_server; nothing changed')
            new = old.replace('tolf_promos.allowed_servers(DB, user_id)', 'tolf_quick.allowed_servers(DB, user_id)')
            new = new.replace('    return server', '''    if server == "moscow":
        provision_on_riga("grant-moscow", user_id)
    return server''')
            replacements.append((node.lineno-1, node.end_lineno, new))
        if node.name == 'passkey_register_finish':
            returns = [n for n in ast.walk(node) if isinstance(n, ast.Return) and isinstance(n.value, ast.Dict)]
            returns = [n for n in returns if 'recoveryCode' in [k.value for k in n.value.keys if isinstance(k, ast.Constant)]]
            if len(returns) != 1 or 'verify_registration_response' not in old:
                raise RuntimeError('Unrecognized registration handler; nothing changed')
            ret = returns[0]
            expr = ast.get_source_segment(source, ret.value)
            indent = ' ' * ret.col_offset
            replacements.append((ret.lineno-1, ret.end_lineno,
                                 indent + 'return tolf_quick.registration_session(' + expr + ', globals())\n'))
    if len(replacements) != 2:
        raise RuntimeError('Expected both API handlers; nothing changed')
    for start, end, text in sorted(replacements, reverse=True):
        lines[start:end] = [text if text.endswith('\n') else text+'\n']
    result = ''.join(lines).replace('tolf_promos.allowed_servers(DB, user_id)', 'tolf_quick.allowed_servers(DB, user_id)')
    result += '\n'+MARKER+'\nimport tolf_quick\ntolf_quick.install(app, globals())\n'
    compile(result, 'main.py', 'exec')
    return result


def main():
    if os.geteuid() != 0 or socket.gethostname() != 'EDISUK':
        raise SystemExit('Run as root on London (EDISUK)')
    root = Path('/opt/tolf-api')
    first = root/'main.py'
    with open('/var/lock/tolf-quick-install.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original = first.read_text()
        modified = patch(original)
        module = zlib.decompress(base64.b64decode(PAYLOAD)).decode()
        compile(module, 'tolf_quick.py', 'exec')
        backup = Path(tempfile.mkdtemp(prefix='tolf-quick-backup-', dir='/root'))
        targets = {first: modified, root/'tolf_quick.py': module}
        existed = {p: p.exists() for p in targets}
        for p in targets:
            if p.exists(): shutil.copy2(p, backup/p.name)
        print('Backup:', backup, flush=True)
        def write(p, value):
            fd, name = tempfile.mkstemp(dir=root, prefix='.quick-')
            try:
                with os.fdopen(fd, 'w') as f:
                    f.write(value); f.flush(); os.fsync(f.fileno())
                owner = first.stat()
                os.chown(name, owner.st_uid, owner.st_gid)
                os.chmod(name, owner.st_mode & 0o777)
                os.replace(name, p)
            finally:
                if os.path.exists(name): os.unlink(name)
        try:
            for p, value in targets.items(): write(p, value)
            subprocess.run(['systemctl', 'restart', 'tolf-api.service'], check=True, timeout=40)
            for attempt in range(8):
                try:
                    with urllib.request.urlopen('https://api.tolf.is/quick-setup/capabilities', timeout=5) as r:
                        data = json.load(r)
                    if data.get('version') != 1 or data.get('servers') != ['riga', 'moscow']:
                        raise RuntimeError('Capabilities mismatch')
                    subprocess.run(['systemctl', 'is-active', '--quiet', 'tolf-api.service'], check=True)
                    break
                except Exception:
                    if attempt == 7: raise
                    time.sleep(1)
        except Exception:
            for p in targets:
                if existed[p]: shutil.copy2(backup/p.name, p)
                else: p.unlink(missing_ok=True)
            subprocess.run(['systemctl', 'restart', 'tolf-api.service'], check=False, timeout=40)
            raise
    print('OK: quick setup v1 enabled. Moscow is available without a promo code.')
    print('Installation did not create VPN users, change passwords or disconnect sessions.')

if __name__ == '__main__':
    main()
