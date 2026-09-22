#!/usr/bin/env python3
"""Install the local user0 routing service; refuses to overwrite an installation."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

SOURCE = Path(__file__).resolve().parent
TARGET = Path('/opt/tolf-user0-routing')
INIT = Path('/etc/init.d/tolf-user0-routing')
STATUS = Path('/var/run/tolf-user0-routing/status.json')
ENV = dict(os.environ, PYTHONPATH='/opt/tolf-routing-python')


def run(args, **kw):
    return subprocess.run(args, check=True, timeout=75, env=ENV, **kw)


def main():
    if os.geteuid() != 0 or not Path('/etc/openwrt_release').exists():
        raise RuntimeError('Run on Moscow OpenWrt as root')
    if TARGET.exists() or TARGET.is_symlink() or INIT.exists() or INIT.is_symlink():
        raise RuntimeError('Installation already exists; nothing changed')
    for tool in ('python3', 'nft', 'dnsmasq', 'conntrack', 'ip', 'ubus'):
        if not shutil.which(tool):
            raise RuntimeError('Missing command: ' + tool)
    for filename in ('service.py', 'core.py'):
        compile((SOURCE / filename).read_text(), filename, 'exec')
    run(['sh', '-n', str(SOURCE / 'tolf-user0-routing.init')])
    sys.path.insert(0, '/opt/tolf-routing-python')
    spec = importlib.util.spec_from_file_location('routing_install_check', SOURCE / 'service.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.check_route()
    module.dns_alive(53)
    module.core.read_bindings()  # Confirm VICI is reachable, even if no user is connected.
    if module.owned_table() or module.core.input_rules():
        raise RuntimeError('Found old service rules; inspect before installing')
    for kind in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
        with socket.socket(socket.AF_INET, kind) as sock:
            sock.bind((module.core.DNS, module.core.PORT))
    # Validate the installed kernel's support without applying any packet rule.
    module.core.nft('''create table inet tolf_user0_install_check { comment "syntax check only"; }
add set inet tolf_user0_install_check delfi4 { type ipv4_addr; flags timeout; timeout 24h; size 4096; }
add chain inet tolf_user0_install_check pre { type filter hook prerouting priority -140; policy accept; }
add rule inet tolf_user0_install_check pre ip saddr 10.10.10.2 ipsec in reqid 1 ipsec in spi 256 ip daddr @delfi4 meta mark set 0x100
''', check=True)
    TARGET.mkdir(mode=0o700)
    init_created = False
    try:
        for filename in ('service.py', 'core.py'):
            shutil.copyfile(SOURCE / filename, TARGET / filename)
            (TARGET / filename).chmod(0o600)
        with INIT.open('x') as handle:
            init_created = True
            handle.write((SOURCE / 'tolf-user0-routing.init').read_text())
        INIT.chmod(0o755)
        run([str(INIT), 'start'])
        ready = False
        for _ in range(20):
            if STATUS.exists():
                data = json.loads(STATUS.read_text())
                if time.time() - data['updated'] < 5:
                    os.kill(data['pid'], 0)
                    ready = True
                    break
            time.sleep(0.5)
        if not ready:
            raise RuntimeError('Service did not report healthy status')
        run([str(INIT), 'enable'])
        run([str(INIT), 'enabled'])
        print('OK: installed and enabled: user0 / delfi.lv -> Moscow')
        print(STATUS.read_text())
        print('Rollback: /etc/init.d/tolf-user0-routing disable; /etc/init.d/tolf-user0-routing stop')
    except BaseException:
        if init_created:
            subprocess.run([str(INIT), 'disable'], timeout=15, env=ENV)
            subprocess.run([str(INIT), 'stop'], timeout=75, env=ENV)
            # Refuse to remove recovery code if cleanup cannot be verified.
            run(['/usr/bin/python3', str(TARGET / 'service.py'), '--cleanup'])
            INIT.unlink()
        shutil.rmtree(TARGET)
        raise


if __name__ == '__main__':
    main()
