#!/usr/bin/python3
"""Fixed-account JSON relay through the existing Riga provisioning gate."""
import json
import os
import signal
import subprocess
import sys
import policy

SSH = ['/usr/bin/ssh', '-T', '-i', '/root/.ssh/id_ed25519_ike_users_sync',
       '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
       '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10',
       'root@10.31.0.1']


def relay(action, raw=b''):
    if action not in ('status', 'apply'):
        raise ValueError('Unsupported action')
    if len(raw) > policy.MAX_BODY:
        raise ValueError('Request too large')
    body = policy.encoded(json.loads(raw)) if action == 'apply' else b''
    result = subprocess.run(SSH + [
        '/usr/bin/python3 /opt/tolf-user0-routing/rpc.py ' + action],
        input=body, capture_output=True, timeout=25, check=False)
    if result.returncode or len(result.stdout) > policy.MAX_BODY:
        raise RuntimeError('Moscow receiver rejected request or is unavailable')
    value = json.loads(result.stdout)
    if (value.get('protocol') != 2 or value.get('status') != 'ok'
            or value.get('node') != 'moscow' or value.get('accountId') != policy.ACCOUNT
            or value.get('vpnUsername') != policy.USERNAME
            or value.get('scope') != 'moscow-ikev2-eap-domain'):
        raise ValueError('Unexpected receiver identity')
    if action == 'apply':
        wanted = json.loads(body)
        if (value.get('acceptedRevision') != wanted['revision']
                or value.get('acceptedDigest') != policy.digest(wanted)):
            raise ValueError('Receiver did not acknowledge the submitted revision')
    return value


def main():
    if os.geteuid() != 0 or len(sys.argv) != 2 or sys.argv[1] not in ('status', 'apply'):
        raise ValueError('Expected root gateway: status or apply')
    # Bound an authenticated caller that leaves stdin open indefinitely.
    signal.alarm(35)
    raw = sys.stdin.buffer.read(policy.MAX_BODY + 1) if sys.argv[1] == 'apply' else b''
    print(json.dumps(relay(sys.argv[1], raw), separators=(',', ':')))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'protocol': 2, 'status': 'error', 'error': str(exc)}))
        sys.exit(1)
