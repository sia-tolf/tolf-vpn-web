#!/usr/bin/env python3
"""Restricted public-certificate provisioning on Riga/Moscow. No private keys."""
import base64
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import uuid

spec = importlib.util.spec_from_file_location('routing', '/usr/local/lib/tolf-windows-routing.py')
routing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routing)

def connection(device, node, mode):
    compact = uuid.UUID(device).hex
    ip, host = routing.HOSTS[node]
    name = 'tolf-cert-' + compact
    return f'''connections {{
    {name} {{
        version = 2
        local_addrs = {ip}
        proposals = aes256-sha256-modp2048
        fragmentation = yes
        send_cert = always
        mobike = yes
        reauth_time = 0
        rekey_time = 0
        unique = replace
        dpd_delay = 30s
        pools = {routing.POOLS[node][mode]}
        local {{
            auth = pubkey
            id = {host}
        }}
        remote {{
            auth = pubkey
            id = "CN=tolf-win-{compact}.tolf.is"
            cacerts = tolf-windows-ca.pem
            pubkeys = tolf-cert-{compact}.pem
        }}
        children {{ {name} {{
            local_ts = 0.0.0.0/0
            remote_ts = dynamic
            esp_proposals = aes256-sha256
            rekey_time = 0
            dpd_action = clear
        }} }}
    }}
}}
'''

def main(args):
    if os.geteuid() != 0 or len(args) != 4 or args[0] not in {'apply', 'remove'}:
        raise ValueError('Invalid certificate operation')
    action, device, node, mode = args
    mode = '' if mode == 'default' else mode
    routing.validate(device, node, mode)
    compact = uuid.UUID(device).hex
    data = json.loads(sys.stdin.read(20000)) if action == 'apply' else {}
    if action == 'apply':
        if set(data) != {'certificate', 'ca', 'publicKey'}: raise ValueError('Invalid public certificate fields')
        for key, marker in [('certificate', 'CERTIFICATE'), ('ca', 'CERTIFICATE'), ('publicKey', 'PUBLIC KEY')]:
            if not isinstance(data[key], str) or not re.fullmatch('-----BEGIN '+marker+'-----\n[A-Za-z0-9+/=\n]+-----END '+marker+'-----\n', data[key]):
                raise ValueError('Invalid certificate encoding')
    # Same global lock as password and routing operations; only public material is transferred.
    with open('/var/lock/tolf-provision.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        routing.preflight(node)
        conf = '/etc/swanctl/conf.d/tolf-cert-' + compact + '.conf'
        pub = '/etc/swanctl/pubkey/tolf-cert-' + compact + '.pem'
        cert = '/etc/swanctl/x509/tolf-cert-' + compact + '.pem'
        ca = '/etc/swanctl/x509ca/tolf-windows-ca.pem'
        writes = {conf: connection(device, node, mode), pub: data.get('publicKey'), cert: data.get('certificate'), ca: data.get('ca')} if action == 'apply' else {}
        body = 'set -eu\numask 077\nmkdir -p /etc/swanctl/pubkey /etc/swanctl/x509 /etc/swanctl/x509ca\n'
        # Pinned authority must never be replaced by a later issuance request.
        if action == 'apply':
            encoded = base64.b64encode(data['ca'].encode()).decode()
            body += '''candidate=$(mktemp /etc/swanctl/.tolf-cert-ca.XXXXXX)
trap 'rm -f "$candidate"' EXIT
'''
            body += f"printf '%s' '{encoded}' | base64 -d > \"$candidate\"\n"
            body += f'if [ -f {ca} ]; then cmp -s {ca} "$candidate"; fi\n'
        # Restore the configuration if loading fails. Files outside this device are untouched.
        backup = conf + '.before-certificate-operation'
        body += f'if [ -f {conf} ]; then cp -p {conf} {backup}; fi\n'
        for path, value in writes.items():
            encoded = base64.b64encode(value.encode()).decode()
            body += f"printf '%s' '{encoded}' | base64 -d > {path}.tmp\nmv {path}.tmp {path}\n"
        if action == 'apply':
            body += f'openssl verify -CAfile {ca} {cert} >/dev/null\n'
            body += 'swanctl --load-creds --noprompt >/dev/null 2>&1\n'
        else:
            body += f'rm -f {conf}\n'
        body += f'''if ! swanctl --load-conns --file /etc/swanctl/swanctl.conf >/dev/null 2>&1; then
    if [ -f {backup} ]; then mv {backup} {conf}; else rm -f {conf}; fi
    swanctl --load-conns --file /etc/swanctl/swanctl.conf >/dev/null 2>&1
    exit 1
fi
rm -f {backup}
'''
        if action == 'remove':
            body += f'''swanctl --terminate --ike tolf-cert-{compact} >/dev/null 2>&1 || true
active=$(swanctl --list-sas --raw)
if printf '%s' "$active" | grep -F 'tolf-cert-{compact}' >/dev/null; then exit 1; fi
rm -f {pub} {cert}
'''
        routing.run(node, body)
    return {'status': 'ok', 'deviceId': device, 'server': node, 'localId': mode, 'authentication': 'certificate'}

if __name__ == '__main__':
    try:
        print(json.dumps(main(sys.argv[1:])))
    except Exception:
        print(json.dumps({'status': 'error', 'error': 'Certificate node operation failed'}))
        sys.exit(1)
