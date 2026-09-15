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

PAYLOAD = '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'
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
