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

PAYLOAD = 'eNq9WG1z27gR/q5fgTofSF4V2pfkrq0zmqtiy4kaR3IlOZeMx6OBSUhiTREMCNpWU//3PguCFCnJPnXaqzzjIfGyWOzu8+wuDw4O/p5HwS3LhM7TY8ZzvRCJjgKuRdhmYa74TSwwG4tARzJ5y0I8zjGbsc8XA3Yv1S3TkomHKNNRMmfdi37mHxwctKJlKpVmIZbqaClaMyWXLJCJFg86jm6YnQ9imWFfu5xa8oTPhSq3z4JEx+XLgmcLbC1f/5HJpBCbcr2oybzAa7koE4ESOqtev8WRFq/L1zyPwkLEjGeap1Ep4sNkctF7CERKl26zkfiWi0w3lvpKZKlMMljCbvrbeDgY2cFW63NvNO4PB6zDfmx96HVP8Yrn784JDxbi5Qmuq2TsHDMnkS8zLZVw2swZiZlQSqiXFzKOgpWdVnbUeWy1WqGYMR7H8l6E00yoO6EyN7xpsxwv0yj0jlsMvxfsvZBzxdPFigULKUlNzpQI5HIpEnjF3CsR2G6cLlX0TzPos+46BvCOPUseJZmVyjXDLAuggVBvzXOq5F2UYSn5nzSKAkSMjuKYiWQmVUBHh8soQYgoyLzDbJ6lIqE9vpELF+UqYVeOiuac7LCUWSDvnWt7XyXmdrNMcOmMdrqwfx5rXCKzd0bYnZBeIZNJvGJ8pnE50rCKzrochFMS4hIMJohmEXbhnZF9Iq3pDXGUZbdiZcKZ5FsLw4uQ4VLs+JeX/VOryJVD8/3QufY8szyR91iaZJjQwTSh67jFjJa3IiExRXD65n2aqzjjM+G+flWsEg9pBNEkA5L+WEHJp3+AoeZuyFdZh04Y98YUbNPT7tcxFDD77yO9KPHl2sD3AbMEUHZp0+k757rNSJrMdef1kecxnhEQDRoLm9IvmkEDTWO+eBBBroWLA897JxP2IzsbDT8Zy2Ts1w+9UY9FYecXuNC11mp7nj8TGjGYCNdbCzVu51Emmlhz3xz9Bf7vBoHME23OneEpdLxqZ0OP/mDcG01YfzAZMhsYmVvYk+iiXWoBQxOlTbluW7vi0WOfu+eXvTFzf2mbP89pNxQsf66lHj9b8Fc//Vwc4IskkCEu5flhNAc9uF6Fwnbl9yiT8Ds86G2OWT08Gy4lncDfdSKpwnwheAgrdyyXNDf54O9pIOVtJFyEbCMmTobDj/0eufqOx7noGOXbbMkfpqDaHeHzw59/fnN0tNsS9FtonRLCOhOVizZFca5E+cKXIkOkdZyYPyAMiJo7zqHj1XGuKpI06Aa7aODW5WlaQ3Msg9tpGCnYgwi9iljPT7kCP7FD5nyj3PWSVmZOY5O/vMV/dwn/dI7kn3CbggSm8tYo+j9GSCMkHedk1OtOemzSfXfeY/0zNhhOWO9LfzwZM6Px1GTbjLkNE5f0Mul9mbCLUf9Td/SVfex9ZaPeGYA1OEGgGqC5YHmGzHIKDOKYk+74BCHR9Fcacw3uXRbSSIHB5fl5mxUZY3NUFfmtOr2aaciEl7RoLoAOZ93L8wlzwOchzOh4uL/XMvv+upHTaYz8XVrYaxiQ+HAfFzSMruT9dMYDpM9Vbf9I3lertFo1Sadwet175W8ViZgyQFLNzKIEgbkhgM6loAHyW9WdkD/nEeUkY0ivQZ520LcI9udCu06xwfHYH4ocMRz13/cHzvU+DPkaDNlPgGb4q5SzViXNb1A7uDBNTQ2LvO8gh2OGqSs8XINaFcMDEMhcpwwZyr9FmJgncrrjPZqLIA+JGAoNQOYtWxGMhFYR6ggk+zCVEYA5yxNTLGbIw4F4ywQqHlsQpELRESiZNGbvk3rBSRWJlYkZGGoRpahdBMDdZtwmBAI4SAK4Zub+RSo3mVshKUISjxsVSVFglLpRNv3uKp9oCRQoUPigYmLKXysPkygyCNgI4ZVTpUtjxVpjKfiPa1QAigoVM5zBUmQTD+5gV9feo6WXJJT32bTIPTi50uLKdQ7t7GEoqGAiCc7FcDxxvGuLHlLAhMphQXOGNA4DnvKbCHEeYY+3xlRt2N32eyOjfHeoaIR5UF7aKrVyeYax7TLscUf6eU5JCpq8rl4xUMLjuCyoa4oSs9lyqdGETC0tImGW4GptQrlgE0vNGwAyRdiu0uWHonRpEHJRwdgT12VMs4b5DdsaUbBiDYbPmy+V2ab9UiUoydUMaEe2LEgZdhVLHh6zMArqBt1gpE1DN0vYfczurWWUVFHlk06pRhEMFZV47eaE5ZW1pJgn8xzZYVNCOU5RKJLaBtBQlduoOjTUFUmDH9CAktAZjxZdjkGkVbJavhHeZk2lyHpVbg/H//jO2at2Paoxc9U017R/wU5NKxKAaKiXbHQndY6jpprf4TLUs+VAKwh2ZiZCRJKpePwmDiQysFsVTYfGz2QTxwCDJpoX2EqMJuFRv+2bg9yCaouR8+HJx2nvC/tX/X3wzmsIEMYQ7B1txH36w55SUm0f8nTZP6boZxH6xRicGa6YypPEVBU7U/gzuH+qURiOWP/9YAiUm5ahjv6qY6miu4ib9ro62rthqBqHwgubeGmv4Uf/3qCH8LxtO/2O3FWWJqgE1mi9pmKkQhclQpq2mDWTxfO2qQmVdfgiZKlGPzW5DREIlxKuqPQ+3mmwp2OCvpRESS4MVjJ+J8LiY5WzbbAXrEsNfBoLXa5iyzwr20gVCHT1YTSbCdNAFJmX7skpQcVih0CsQ2lpsrbPPgqB6EzKI8rCLqPd9JmM6gRq4SkzoCaqIXTT5EVVZUzqmEh3fkez7AmXTcgcXF6cUhvTiLJxb1JFSOcXixA8rDFCo3S7TtUSbIbmwfOYMbjZAzFFs70DN/8P7FTkbr7pVQg6rkG9BM5xdYV1Vjuu8s0ztnBApDzuh/QVMFMOBU+ZbilsKIkV5bhDKSpMsk8oi2mxlvHsOWKiteN1uYf+ypHJqUCfFvYSimQ68oxDdG1mlMeiWP64ySIVZZBeZebdDjAU6xzmapbFZXnRhhnto7mxgck6qqgJdBK+NPf71R7x23G0dfP9fIJ2lge3eDrDrbimM9P0du48biQ8WGgnF1I5dZcmU/reqqiGMpG6G3LWKuUW9C6zKBbruqu9jrXtUN+twZPp/YkzC0/seWQt0zd4iXgF408f+oKd0Dm0dMlXbAHOqrE1dVyg6QV9suU3hpTN91uO0gUMjvI3XvlPyobNcbZftBlT+ixH1AqmJEHE/v+JRxrku68N9/eb/ZyKBpW+e6FDdklUu6jfS31pyNbSheBLFTvefrXUT0evqJks9rF7XuTeolsR4X9fSz2ZGCzvFwltm/UrUm0W0ju7qNqtj40xrupDRAZ7ce6uzuvfk0EnAQ=='
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
