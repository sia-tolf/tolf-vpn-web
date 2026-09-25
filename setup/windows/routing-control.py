#!/usr/bin/env python3
"""Root-only Riga controller. Never reads or returns EAP secrets.

The EAP identity dispatcher supports strongSwan 6.0.1: it requests the client's
identity, then its deliberately unsatisfied group constraint forces selection
of the authenticated identity's connection. Exact local addresses rank these
connections ahead of the existing wildcard Windows fallback. Existing explicit
IKE identities (sr/ru/lv/ch) retain their more specific identity match.
"""
import fcntl
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import tempfile
import uuid

ROOT = Path('/var/lib/ike-users/windows-routing')
CONF = '/etc/swanctl/conf.d/tolf-windows-managed.conf'
MODES = {'riga': ['sr', 'ru'], 'moscow': ['', 'sr', 'ru', 'lv']}
POOLS = {'riga': {'sr': 'vpn-pool-riga-sr', 'ru': 'vpn-pool-riga-ru'},
         'moscow': {'': 'vpn-pool', 'sr': 'vpn-pool-rf', 'ru': 'vpn-pool-ru', 'lv': 'vpn-pool-ee'}}
def resolve_ipv4(host):
    addresses = {entry[4][0] for entry in socket.getaddrinfo(
        host, None, family=socket.AF_INET, type=socket.SOCK_STREAM
    )}
    if len(addresses) != 1:
        raise RuntimeError('VPN entry must resolve to exactly one IPv4 address: ' + host)
    return addresses.pop()


HOST_NAMES = {'riga': 'ikev2-riga.tolf.is', 'moscow': 'ikev2.tolf.is'}
# Resolve once per controller invocation, including preflight and rollback.
HOSTS = {node: (resolve_ipv4(host), host) for node, host in HOST_NAMES.items()}
SSH = ['/usr/bin/ssh', '-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
       '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10',
       '-i', '/root/.ssh/id_ed25519_ike_users_sync', 'root@10.31.0.1', 'sh', '-s']


def run(node, script):
    result = subprocess.run(['sh', '-s'] if node == 'riga' else SSH,
                            input=script, text=True, capture_output=True, timeout=35)
    if result.returncode:
        raise RuntimeError('Windows routing operation failed on ' + node)
    return result.stdout


def validate(device, server, mode):
    if str(uuid.UUID(device)) != device or server not in MODES or mode not in MODES[server]:
        raise ValueError('Invalid Windows routing assignment')


def render(node, records):
    rows = sorted((device, value) for device,value in records.items() if value['server'] == node)
    if not rows:
        return '# Managed Windows routing: no assigned devices.\n'
    ip, host = HOSTS[node]
    def connection(name, eap_id, pool, dispatcher=False):
        group = '\n            groups = tolf-windows-dispatch-no-members' if dispatcher else ''
        return f'''    {name} {{
        version = 2
        local_addrs = {ip}
        remote_addrs = %any
        proposals = aes256-sha256-modp2048
        reauth_time = 0
        rekey_time = 0
        unique = never
        dpd_delay = 30s
        pools = {pool}
        local {{ auth = pubkey
            id = {host}
        }}
        remote {{ auth = eap-mschapv2
            id = %any
            eap_id = {eap_id}{group}
        }}
        children {{ {name} {{
            local_ts = 0.0.0.0/0
            remote_ts = dynamic
            esp_proposals = aes256-sha256
            rekey_time = 0
            dpd_action = none
        }} }}
    }}
'''
    result = 'connections {\n' + connection('tolf-win-dispatch', '%any', POOLS[node][rows[0][1]['mode']], True)
    for device, value in rows:
        validate(device, value['server'], value['mode'])
        result += connection('tolf-win-'+uuid.UUID(device).hex, 'user_'+uuid.UUID(device).hex, POOLS[node][value['mode']])
    return result + '}\n'


def preflight(node):
    # Only these pool names are read; no credential files are inspected.
    if HOSTS[node][0]+'/' not in run(node, 'ip -4 -o addr show\n'):
        raise RuntimeError('Expected local VPN address missing on '+node)
    version = run(node, 'swanctl --version --daemon 2>/dev/null\n')
    if not version.startswith('strongSwan 6.'):
        raise RuntimeError('Unsupported strongSwan daemon on '+node)
    pool_output = run(node, 'swanctl --list-pools 2>/dev/null\n')
    names = {line.split()[0] for line in pool_output.splitlines() if line.split()}
    if not set(POOLS[node].values()) <= names:
        raise RuntimeError('Required Windows address pools missing on '+node)
    # Full configuration loading is essential: loading only a fragment unloads
    # unrelated connections. Refuse an installation without the standard include.
    run(node, "grep -Eq '^[[:space:]]*include[[:space:]]+(conf.d/\\*\\.conf|/etc/swanctl/conf.d/\\*\\.conf)[[:space:]]*$' /etc/swanctl/swanctl.conf\n")


def replace(node, content):
    # Rendered content contains only fixed strings and validated UUIDs/modes.
    # Keep a node-local copy for restoring runtime configuration on reload error.
    script = f'''set -eu
umask 077
target={shlex.quote(CONF)}
temp=$(mktemp /etc/swanctl/conf.d/.tolf-win.XXXXXX)
backup=$(mktemp /etc/swanctl/conf.d/.tolf-win-backup.XXXXXX)
existed=0
if [ -f "$target" ]; then cp -p "$target" "$backup"; existed=1; fi
trap 'rm -f "$temp" "$backup"' EXIT
cat > "$temp" <<'TOLF_WINDOWS_END'
{content}TOLF_WINDOWS_END
mv "$temp" "$target"
if ! swanctl --load-conns --file /etc/swanctl/swanctl.conf >/dev/null 2>&1; then
    if [ "$existed" = 1 ]; then cp -p "$backup" "$target"; else rm -f "$target"; fi
    swanctl --load-conns --file /etc/swanctl/swanctl.conf >/dev/null 2>&1 || exit 2
    exit 1
fi
'''
    run(node, script)


def atomic(path, value):
    fd, temp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(value, f); f.flush(); os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)


def change(records, updated):
    for node in HOSTS: preflight(node)
    # Save the recovery journal BEFORE either host is changed. A retry after a
    # timeout/process death restores both hosts before processing a new request.
    atomic(ROOT/'recovery.json', records)
    try:
        for node in HOSTS: replace(node, render(node, updated))
        atomic(ROOT/'assignments.json', updated)
    except Exception:
        # Keep journal if restoration fails; never report success in that case.
        for node in HOSTS: replace(node, render(node, records))
        (ROOT/'recovery.json').unlink()
        raise
    (ROOT/'recovery.json').unlink()


def main(args):
    if os.geteuid() != 0: raise RuntimeError('Root required')
    if args == ['capabilities']:
        if not (ROOT/'enabled').is_file(): raise RuntimeError('Windows routing is not enabled')
        for node in HOSTS: preflight(node)
        return {'status': 'ok', 'protocol': 1, 'modes': MODES}
    if len(args) not in (2, 4) or args[0] not in ('apply', 'remove'):
        raise ValueError('Invalid routing command')
    action, device = args[:2]
    if str(uuid.UUID(device)) != device: raise ValueError('Invalid device')
    if action == 'apply':
        if len(args) != 4: raise ValueError('Missing routing selection')
        server, mode = args[2], '' if args[3] == 'default' else args[3]
        validate(device, server, mode)
    elif len(args) != 2: raise ValueError('Invalid removal command')
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (ROOT/'lock').open('a') as lock, open('/var/lock/tolf-provision.lock', 'a') as provision_lock:
        fcntl.flock(provision_lock, fcntl.LOCK_EX)
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = ROOT/'assignments.json'
        records = json.loads(path.read_text()) if path.exists() else {}
        recovery = ROOT/'recovery.json'
        if recovery.exists():
            # assignments.json is the commit point; finish a committed update,
            # otherwise restore its predecessor after an interrupted update.
            for node in HOSTS: replace(node, render(node, records))
            atomic(path, records); recovery.unlink()
        updated = dict(records)
        if action == 'apply':
            if not (ROOT/'enabled').is_file(): raise RuntimeError('Windows routing is not enabled')
            expected = {'server': server, 'mode': mode}
            if device in records and records[device] != expected:
                raise RuntimeError('Existing device routing cannot be reassigned')
            updated[device] = expected
        else:
            updated.pop(device, None)
        if updated != records: change(records, updated)
        return {'status': 'ok', **({'server': server, 'localId': mode} if action == 'apply' else {})}


if __name__ == '__main__':
    try:
        print(json.dumps(main(sys.argv[1:])))
    except Exception as exc:
        # Deliberately omit subprocess output/configuration from the RPC response.
        print(json.dumps({'status': 'error', 'error': str(exc) if isinstance(exc, (ValueError, RuntimeError)) else 'Routing update failed'}))
        sys.exit(1)
