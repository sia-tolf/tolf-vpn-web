#!/usr/bin/env python3
"""Bounded user0/delfi.lv pilot. No API acknowledgement or boot installation.

Stop via SIGTERM/SIGINT/SIGHUP for cleanup; SIGKILL cannot run cleanup.
All packet rules match a VICI-authenticated, installed inbound CHILD_SA.
"""
import argparse
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time

TABLE = 'tolf_personal_pilot'
TAG = 'tolf-personal-pilot-v1'
DNS = '10.254.0.53'
PORT = 1053
LOCK = '/var/run/tolf-personal-pilot.lock'
STOP = False


def command(args, **kwargs):
    return subprocess.run(args, timeout=10, check=True, **kwargs)


def nft(script, check=False):
    command(['nft'] + (['--check'] if check else []) + ['-f', '-'],
            input=script, text=True, capture_output=True)


def decode(value):
    if isinstance(value, bytes):
        return value.decode('utf-8')
    if isinstance(value, dict):
        return {decode(k): decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value


def bindings(events):
    """Never substitute caller-supplied IKE identity for an absent EAP ID."""
    result = set()
    owners = {}
    for event in events:
        for name, sa in decode(event).items():
            if sa.get('state') != 'ESTABLISHED':
                continue
            for value in sa.get('remote-vips', []):
                address = ipaddress.ip_address(value)
                if address.version != 4:
                    continue
                vip = str(address)
                owners.setdefault(vip, set()).add(sa['uniqueid'])
                if (name != 'ikev2-eap-domain'
                        or sa.get('remote-eap-id') != 'user0'):
                    continue
                # Pilot restricted to the pool verified on the node.
                if address not in ipaddress.ip_network('10.10.10.0/24'):
                    raise ValueError('Unexpected user0 address pool')
                for child in sa.get('child-sas', {}).values():
                    if (child.get('state') not in ('INSTALLED', 'REKEYING')
                            or child.get('protocol') != 'ESP'
                            or child.get('mode') != 'TUNNEL'
                            or child.get('remote-ts') != [vip + '/32']):
                        continue
                    reqid = int(child['reqid'])
                    spi = int(child['spi-in'], 16)
                    if not 0 < reqid < 2**32 or not 255 < spi < 2**32:
                        raise ValueError('Invalid IPsec identifiers')
                    result.add((vip, reqid, spi))
    if any(len(owners[vip]) != 1 for vip, _, _ in result):
        raise ValueError('Ambiguous virtual address ownership')
    return sorted(result)


def read_bindings():
    import vici
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(4)
        sock.connect('/var/run/charon.vici')
        return bindings(list(vici.Session(sock).list_sas()))


def match(binding):
    vip, reqid, spi = binding
    return f'ip saddr {vip} ipsec in reqid {reqid} ipsec in spi {spi}'


def rule_batch(current):
    lines = [f'flush chain inet {TABLE} {name}' for name in
             ('guard', 'dns_redirect', 'mark_moscow', 'verify_exit')]
    for item in current:
        m = match(item)
        lines += [
            f'add rule inet {TABLE} guard ip daddr {DNS} meta l4proto {{ tcp, udp }} '
            f'th dport {PORT} {m} ct status dnat counter accept',
            f'add rule inet {TABLE} dns_redirect {m} ip daddr {DNS} '
            f'meta l4proto {{ tcp, udp }} th dport 53 counter dnat ip to {DNS}:{PORT}',
            f'add rule inet {TABLE} mark_moscow {m} ip daddr @delfi4 counter meta mark set 0x100',
            f'add rule inet {TABLE} verify_exit {m} ip daddr @delfi4 meta mark 0x100 '
            'oifname "br-lan" counter',
        ]
    lines.append(f'add rule inet {TABLE} guard ip daddr {DNS} '
                 f'meta l4proto {{ tcp, udp }} th dport {PORT} counter drop')
    return '\n'.join(lines) + '\n'


def input_rules():
    data = json.loads(command(
        ['nft', '-j', '-a', 'list', 'chain', 'inet', 'fw4', 'input'],
        capture_output=True, text=True).stdout)
    return [x['rule'] for x in data['nftables']
            if x.get('rule', {}).get('comment') == TAG]


def ensure_input(current):
    existing = input_rules()
    # Exact bindings also live in fw4. No unconditional high-port allowance.
    desired = '\n'.join(
        f'insert rule inet fw4 input {match(b)} ip daddr {DNS} '
        f'meta l4proto {{ tcp, udp }} th dport {PORT} ct status dnat '
        f'counter accept comment "{TAG}"' for b in current)
    return existing, desired


def replace_input(existing, desired):
    removals = '\n'.join(f'delete rule inet fw4 input handle {x["handle"]}'
                         for x in existing)
    if removals or desired:
        nft(removals + '\n' + desired + '\n')


def clean_connections(addresses):
    for address in sorted(set(addresses)):
        ipaddress.IPv4Address(address)
        for proto in ('udp', 'tcp'):
            result = subprocess.run([
                'conntrack', '-D', '-f', 'ipv4', '-p', proto,
                '-s', address, '-d', DNS, '--dport', '53',
                '--reply-port-src', str(PORT),
            ], capture_output=True, text=True, timeout=10)
            if result.returncode and not (
                    result.returncode == 1
                    and '0 flow entries have been deleted' in result.stderr):
                raise RuntimeError('Could not clear pilot DNS connections')


def cleanup(state):
    errors = []
    # Idempotent cleanup; treat already-removed objects as OK.
    for action in (
        lambda: subprocess.run(['nft', 'delete', 'table', 'inet', TABLE],
                               capture_output=True, timeout=10),
        lambda: replace_input(input_rules(), ''),
        lambda: clean_connections(state.get('addresses', [])),
    ):
        try:
            result = action()
            if isinstance(result, subprocess.CompletedProcess) and result.returncode:
                # Verify absence instead of silently accepting a failed delete.
                listing = json.loads(command(['nft', '-j', 'list', 'tables'],
                                             capture_output=True, text=True).stdout)
                if any(x.get('table', {}).get('name') == TABLE
                       and x['table'].get('family') == 'inet'
                       for x in listing['nftables']):
                    raise RuntimeError('Pilot table could not be removed')
        except Exception as exc:
            errors.append(str(exc))
    if errors:
        raise RuntimeError('Cleanup failed: ' + '; '.join(errors))


def run_pilot(seconds):
    global STOP
    if os.geteuid() != 0:
        raise RuntimeError('Run as root on Moscow OpenWrt')
    if not Path('/etc/openwrt_release').exists():
        raise RuntimeError('This pilot is for OpenWrt only')
    if not Path(__file__).is_file():
        raise RuntimeError('Save this program to a file before running')
    lock = open(LOCK, 'w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    # Refuse to adopt or destroy stale objects without review.
    tables = json.loads(command(['nft', '-j', 'list', 'tables'],
                                text=True, capture_output=True).stdout)
    if any(x.get('table', {}).get('name') == TABLE
           and x['table'].get('family') == 'inet' for x in tables['nftables']):
        raise RuntimeError('Pilot table already exists; inspect before retrying')
    if input_rules():
        raise RuntimeError('Pilot input rules already exist')
    for kind in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
        with socket.socket(socket.AF_INET, kind) as sock:
            sock.bind((DNS, PORT))
    initial = read_bindings()
    if not initial:
        raise RuntimeError('Connect user0 to Moscow before starting the pilot')
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, lambda *_: globals().__setitem__('STOP', True))
    with tempfile.TemporaryDirectory(prefix='tolf-personal-pilot-') as directory:
        root = Path(directory)
        conf = root / 'dnsmasq.conf'
        conf.write_text(f'port={PORT}\nlisten-address={DNS}\nbind-interfaces\n'
                        f'no-resolv\nno-hosts\ncache-size=0\nuser=root\n'
                        f'server={DNS}#53\nnftset=/delfi.lv/4#inet#{TABLE}#delfi4\n'
                        'log-facility=-\n')
        command(['dnsmasq', '--test', '--conf-file=' + str(conf)])
        setup = f'''create table inet {TABLE}
add set inet {TABLE} delfi4 {{ type ipv4_addr; size 4096; }}
add chain inet {TABLE} guard {{ type filter hook input priority -10; policy accept; }}
add chain inet {TABLE} dns_redirect {{ type nat hook prerouting priority -101; policy accept; }}
add chain inet {TABLE} mark_moscow {{ type filter hook prerouting priority -140; policy accept; }}
add chain inet {TABLE} verify_exit {{ type filter hook forward priority -5; policy accept; }}
'''
        nft(setup + rule_batch([]), check=True)
        state = dict(addresses=[], deadline=time.monotonic() + seconds)
        worker = None
        created = False
        try:
            nft(setup + rule_batch([]))
            created = True
            worker = subprocess.Popen(['dnsmasq', '--keep-in-foreground',
                                       '--conf-file=' + str(conf)])
            time.sleep(0.3)
            if worker.poll() is not None:
                raise RuntimeError('DNS worker failed to start')
            previous = []
            last_report = 0
            print(f'Pilot active for {seconds}s; user0 / delfi.lv -> Moscow', flush=True)
            while not STOP and time.monotonic() < state['deadline']:
                if worker.poll() is not None:
                    raise RuntimeError('DNS worker stopped')
                current = read_bindings()
                # Save cleanup addresses before exposing any NAT mapping.
                state['addresses'] = sorted(set(state['addresses']) | {b[0] for b in current})
                existing, desired = ensure_input(current)
                if current != previous:
                    nft(rule_batch(current))
                    replace_input(existing, desired)
                    clean_connections({b[0] for b in previous} - {b[0] for b in current})
                    print('Authenticated bindings:', current, flush=True)
                    previous = current
                elif len(existing) != len(current):
                    # fw4 reload removed the runtime input exceptions.
                    replace_input(existing, desired)
                    print('Restored firewall input exceptions', flush=True)
                if time.monotonic() - last_report >= 30:
                    command(['nft', 'list', 'chain', 'inet', TABLE, 'verify_exit'])
                    last_report = time.monotonic()
                time.sleep(2)
        finally:
            try:
                if created:
                    try:
                        subprocess.run(['nft', 'list', 'table', 'inet', TABLE], timeout=10)
                    finally:
                        # A failed diagnostic must never skip rule withdrawal.
                        cleanup(state)
                    print('Pilot rules and DNS connections removed', flush=True)
            finally:
                if worker is not None and worker.poll() is None:
                    worker.terminate()
                    try:
                        worker.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        worker.kill()
                        worker.wait()



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=int, default=180)
    args = parser.parse_args()
    if not 30 <= args.seconds <= 600:
        parser.error('Pilot duration must be between 30 and 600 seconds')
    run_pilot(args.seconds)



if __name__ == '__main__':
    main()
