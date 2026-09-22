#!/usr/bin/env python3
"""Upgrade the verified local user0 service to revisioned delivery, retaining its rule."""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time

SOURCE = Path(__file__).resolve().parent
TARGET = Path('/opt/tolf-user0-routing')
INIT = '/etc/init.d/tolf-user0-routing'
STATUS = Path('/var/run/tolf-user0-routing/status.json')
ENV = dict(os.environ, PYTHONPATH='/opt/tolf-routing-python')
OLD = {
    'core.py': '55efe3d4573b1f5e80f8d9d6701d081a7a78c4521896b7037e4b44de21d7a5b5',
    'service.py': 'e2442140e1253a12f7be5c4dff57231439e934cd12c20d38ea0205ba2d350e6a',
}
NEW = ('service.py', 'policy.py', 'rpc.py')


def run(args, **kw):
    return subprocess.run(args, env=ENV, check=True, timeout=75, **kw)


def atomic(path, content):
    fd, name = tempfile.mkstemp(prefix='.receiver-stage-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def wait_ready(protocol=None):
    for _ in range(40):
        try:
            value = json.loads(STATUS.read_text())
            if 0 <= time.time() - value['updated'] < 5 and (
                    protocol is None or value.get('protocol') == protocol):
                os.kill(int(value['pid']), 0)
                return value
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(0.5)
    raise RuntimeError('Routing service did not become healthy')


def main():
    if os.geteuid() != 0 or not Path('/etc/openwrt_release').exists():
        raise RuntimeError('Run as root on Moscow OpenWrt')
    sys.path.insert(0, '/opt/tolf-routing-python')
    with open('/var/lock/tolf-user0-receiver-install.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for filename, expected in OLD.items():
            path = TARGET / filename
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise RuntimeError('Existing file differs; no changes made: ' + filename)
        for name in ('policy.py', 'rpc.py', 'policy.json'):
            if (TARGET / name).exists() or (TARGET / name).is_symlink():
                raise RuntimeError('Receiver already exists; no changes made')
        run([INIT, 'running'])
        was_enabled = subprocess.run([INIT, 'enabled'], env=ENV).returncode == 0
        before = wait_ready()
        if before.get('rule') != 'user0: delfi.lv -> moscow':
            raise RuntimeError('Unexpected existing rule; no changes made')
        for filename in NEW:
            compile((SOURCE / filename).read_bytes(), filename, 'exec')
        spec = importlib.util.spec_from_file_location('receiver_preflight', SOURCE / 'service.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        initial = module.policy.bootstrap()
        module.check_route(initial)
        module.dns_alive(53)
        module.core.read_bindings()
        table = 'tolf_receiver_syntax_check'
        batch = f'''create table inet {table}
add set inet {table} moscow4 {{ type ipv4_addr; flags timeout; timeout 24h; size 4096; }}
add set inet {table} riga4 {{ type ipv4_addr; flags timeout; timeout 24h; size 4096; }}
add chain inet {table} guard {{ type filter hook input priority -10; policy accept; }}
add chain inet {table} dns_redirect {{ type nat hook prerouting priority -101; policy accept; }}
add chain inet {table} mark_personal {{ type filter hook prerouting priority -140; policy accept; }}
add chain inet {table} verify_exit {{ type filter hook forward priority -5; policy accept; }}
'''
        module.core.nft(batch + module.policy.nft_rules([('10.10.10.2', 1, 256)], table,
                        '10.254.0.53', 1053, initial), check=True)
        backup = Path(tempfile.mkdtemp(prefix='tolf-routing-receiver-backup-', dir='/root'))
        shutil.copy2(TARGET / 'service.py', backup / 'service.py')
        rollback = f'''#!/usr/bin/env python3
import os, subprocess
from pathlib import Path
target = Path({str(TARGET)!r})
init = {INIT!r}
env = dict(os.environ, PYTHONPATH='/opt/tolf-routing-python')
subprocess.run([init, 'stop'], check=True, timeout=75, env=env)
subprocess.run(['/usr/bin/python3', str(target/'service.py'), '--cleanup'], check=True, timeout=75, env=env)
previous = Path(__file__).with_name('service.py').read_bytes()
temporary = target/'.restore-service.py'
temporary.write_bytes(previous)
temporary.chmod(0o600)
temporary.replace(target/'service.py')
for name in ('policy.py', 'rpc.py', 'policy.json', 'policy.lock'):
    (target/name).unlink(missing_ok=True)
subprocess.run([init, 'start'], check=True, timeout=75, env=env)
print('Previous local user0 rule restored; check service status.')
'''
        (backup / 'rollback.py').write_text(rollback)
        print('Backup:', backup, flush=True)
        changed = False
        try:
            run([INIT, 'stop'])
            run(['/usr/bin/python3', str(TARGET / 'service.py'), '--cleanup'])
            changed = True
            # Dependencies are installed before the updated entry point.
            for filename in ('policy.py', 'rpc.py'):
                atomic(TARGET / filename, (SOURCE / filename).read_bytes())
            atomic(TARGET / 'policy.json', module.policy.encoded(initial))
            atomic(TARGET / 'service.py', (SOURCE / 'service.py').read_bytes())
            run([INIT, 'start'])
            value = wait_ready(module.policy.PROTOCOL)
            if value.get('policyDigest') != module.policy.digest(initial):
                raise RuntimeError('Initial rule was not preserved')
            result = json.loads(run(['/usr/bin/python3', str(TARGET / 'rpc.py'), 'status'],
                                    capture_output=True, text=True).stdout)
            if result.get('appliedRevision') != 0 or result.get('state') not in ('applied', 'ready'):
                raise RuntimeError('Receiver did not acknowledge the initial rule')
            if was_enabled:
                run([INIT, 'enabled'])
            print('OK: revisioned receiver installed; delfi.lv -> Moscow preserved')
            print(json.dumps(result))
            print('Rollback: python3 ' + str(backup / 'rollback.py'))
        except BaseException:
            if changed:
                run(['/usr/bin/python3', str(backup / 'rollback.py')])
            else:
                run([INIT, 'start'])
            raise


if __name__ == '__main__':
    main()
