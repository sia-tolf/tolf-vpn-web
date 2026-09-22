#!/usr/bin/env python3
"""Account-scoped desired-policy receiver, with observed runtime acknowledgements."""
import ctypes
import fcntl
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import signal
import socket
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('routing_core', ROOT / 'core.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
spec = importlib.util.spec_from_file_location('routing_policy', ROOT / 'policy.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)
core.TABLE = 'tolf_user0_routing'
core.TAG = 'tolf-user0-routing-v1'
RUNTIME = Path('/var/run/tolf-user0-routing')
OWNER = 'TOLF local user0 routing v1'
STOP = False


def log(message):
    print(message, flush=True)


def stop(*args):
    global STOP
    STOP = True


def state_write(path, value):
    temporary = path.with_suffix('.new')
    temporary.write_text(json.dumps(value))
    temporary.replace(path)


def owned_table():
    data = json.loads(core.command(['nft', '-j', 'list', 'tables'],
                                  capture_output=True, text=True).stdout)
    found = any(x.get('table', {}).get('name') == core.TABLE
                and x['table'].get('family') == 'inet' for x in data['nftables'])
    if found:
        data = json.loads(core.command(['nft', '-j', 'list', 'table', 'inet', core.TABLE],
                                      capture_output=True, text=True).stdout)
        table = next(x['table'] for x in data['nftables'] if 'table' in x)
        if table.get('comment') != OWNER:
            raise RuntimeError('Refusing to modify a table without our ownership comment')
    return found


def remembered_addresses():
    path = RUNTIME / 'addresses.json'
    values = json.loads(path.read_text()) if path.exists() else []
    if not isinstance(values, list) or len(values) > 256:
        raise ValueError('Invalid recovery state')
    for value in values:
        if ipaddress.IPv4Address(value) not in ipaddress.ip_network('10.10.10.0/24'):
            raise ValueError('Invalid recovery address')
    return values


def recover():
    owned_table()
    core.cleanup({'addresses': remembered_addresses()})
    (RUNTIME / 'status.json').unlink(missing_ok=True)


def dns_alive(port):
    """Probe the local Unbound portal record without external DNS dependency."""
    token = os.urandom(2)
    name = b''.join(bytes([len(x)]) + x for x in b'portal.vpn.tolf.is'.split(b'.')) + b'\0'
    query = token + struct.pack('!HHHHH', 0x100, 1, 0, 0, 0) + name + b'\0\1\0\1'
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(2)
        sock.connect((core.DNS, port))
        sock.send(query)
        data = sock.recv(4096)
    if len(data) < 12 or data[:2] != token or not data[2] & 128 or data[3] & 15:
        raise RuntimeError('DNS health probe failed')
    if struct.unpack('!H', data[6:8])[0] == 0:
        raise RuntimeError('DNS health probe returned no portal record')


def die_with_parent(parent):
    # DNS must not survive an unexpected death of this controller.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
        os._exit(125)
    if os.getppid() != parent:
        os._exit(125)


def check_route(configured=None):
    groups = (configured or policy.bootstrap())['routingRules']
    for exit_name, mark, devices in [('moscow', '0x100', ('br-lan',)),
                                     ('riga', '0x200', ('awgriga', 'gre4-riga_gre'))]:
        if not groups[exit_name]:
            continue
        data = core.command([
            'ip', '-4', 'route', 'get', '104.20.18.136',
            'from', '10.10.10.2', 'iif', 'br-lan', 'mark', mark
        ], capture_output=True, text=True).stdout.split()
        if 'dev' not in data or data[data.index('dev') + 1] not in devices:
            raise RuntimeError(exit_name + ' mark selects an unexpected output')


def conflict_count():
    sets = []
    for name in ('moscow4', 'riga4'):
        value = json.loads(core.command(['nft', '-j', 'list', 'set', 'inet', core.TABLE, name],
                                       capture_output=True, text=True).stdout)
        sets.append(policy.nft_addresses(value))
    return len(sets[0] & sets[1])


def run_service(configured=None):
    configured = configured or policy.load()
    fingerprint = policy.digest(configured)
    for kind in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
        with socket.socket(socket.AF_INET, kind) as sock:
            sock.bind((core.DNS, core.PORT))
    check_route(configured)
    dns_alive(53)
    config = RUNTIME / 'dnsmasq.conf'
    config.write_text(
        f'port={core.PORT}\nlisten-address={core.DNS}\nbind-interfaces\n'
        f'pid-file={RUNTIME}/dnsmasq.pid\nno-resolv\nno-hosts\n'
        'cache-size=0\nmax-ttl=300\nuser=root\n'
        f'server={core.DNS}#53\n' + ''.join(
            f'nftset=/{domain}/4#inet#{core.TABLE}#{exit_name}4\n'
            for exit_name in ('moscow', 'riga') for domain in configured['routingRules'][exit_name]
        ) + 'log-facility=-\n')
    core.command(['dnsmasq', '--test', '--conf-file=' + str(config)])
    setup = f'''create table inet {core.TABLE} {{ comment "{OWNER}"; }}
add set inet {core.TABLE} moscow4 {{ type ipv4_addr; flags timeout; timeout 24h; size 4096; }}
add set inet {core.TABLE} riga4 {{ type ipv4_addr; flags timeout; timeout 24h; size 4096; }}
add chain inet {core.TABLE} guard {{ type filter hook input priority -10; policy accept; }}
add chain inet {core.TABLE} dns_redirect {{ type nat hook prerouting priority -101; policy accept; }}
add chain inet {core.TABLE} mark_personal {{ type filter hook prerouting priority -140; policy accept; }}
add chain inet {core.TABLE} verify_exit {{ type filter hook forward priority -5; policy accept; }}
'''
    # The service itself may probe its private listener; forwarded clients still
    # require authenticated IPsec selectors and a translated DNS connection.
    def rules(current):
        return policy.nft_rules(current, core.TABLE, core.DNS, core.PORT, configured)

    core.nft(setup + rules([]), check=True)
    worker = None
    created = False
    addresses = set(remembered_addresses())
    try:
        core.nft(setup + rules([]))
        created = True
        parent = os.getpid()
        worker = subprocess.Popen(['dnsmasq', '--keep-in-foreground', '--conf-file=' + str(config)],
                                  preexec_fn=lambda: die_with_parent(parent))
        time.sleep(0.5)
        if worker.poll() is not None:
            raise RuntimeError('Private dnsmasq failed to start')
        dns_alive(core.PORT)
        previous = []
        last_health = time.monotonic()
        log('Policy ready: user0 revision ' + str(configured['revision']))
        while not STOP:
            if policy.digest(policy.load()) != fingerprint:
                log('New desired policy detected; replacing the previous rules')
                return
            if worker.poll() is not None:
                raise RuntimeError('Private dnsmasq stopped')
            if not owned_table():
                raise RuntimeError('Routing table disappeared; restarting cleanly')
            current = core.read_bindings()
            if not any(configured['routingRules'].values()):
                current = []
            new_addresses = addresses | {b[0] for b in current}
            if new_addresses != addresses:
                state_write(RUNTIME / 'addresses.json', sorted(new_addresses))
                addresses = new_addresses
            existing, desired = core.ensure_input(current)
            if current != previous:
                # Both tables are updated in one nft transaction.
                removals = '\n'.join(f'delete rule inet fw4 input handle {x["handle"]}' for x in existing)
                core.nft(rules(current) + removals + '\n' + desired + '\n')
                core.clean_connections({b[0] for b in previous} - {b[0] for b in current})
                log('Authenticated bindings: ' + repr(current))
                previous = current
            elif len(existing) != len(current):
                core.replace_input(existing, desired)
                log('Restored fw4 input exceptions')
            if time.monotonic() - last_health >= 15:
                dns_alive(core.PORT)
                check_route(configured)
                last_health = time.monotonic()
            state_write(RUNTIME / 'status.json', {
                'pid': os.getpid(), 'updated': time.time(), 'bindings': current,
                'protocol': policy.PROTOCOL,
                'policyRevision': configured['revision'], 'policyDigest': fingerprint,
                'routingRules': configured['routingRules'],
                'conflictingAddresses': conflict_count(), 'apiAcknowledged': False
            })
            time.sleep(2)
    finally:
        try:
            if created:
                core.cleanup({'addresses': addresses})
        finally:
            (RUNTIME / 'status.json').unlink(missing_ok=True)
            if worker is not None and worker.poll() is None:
                worker.terminate()
                try:
                    worker.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    worker.kill()
                    worker.wait()


def main():
    if os.geteuid() != 0 or not Path('/etc/openwrt_release').exists():
        raise RuntimeError('Run on Moscow OpenWrt as root')
    if RUNTIME.is_symlink():
        raise RuntimeError('Unexpected runtime symlink')
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    lock = open(RUNTIME / 'lock', 'w')
    deadline = time.monotonic() + (65 if '--cleanup' in sys.argv else 0)
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.2)
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, stop)
    recover()
    if '--cleanup' not in sys.argv:
        while not STOP:
            run_service(policy.load())


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        log('Routing service error: ' + repr(exc))
        if isinstance(exc, subprocess.CalledProcessError):
            log(str(exc.stderr or ''))
        sys.exit(1)
