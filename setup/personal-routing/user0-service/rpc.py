#!/usr/bin/env python3
"""Root-only JSON RPC, intended for the existing authenticated SSH channel."""
import fcntl
import json
import os
from pathlib import Path
import sys
import tempfile
import time

import policy

ROOT = Path(__file__).resolve().parent
STATUS = Path('/var/run/tolf-user0-routing/status.json')


def write_policy(value):
    target = policy.POLICY_FILE
    fd, temporary = tempfile.mkstemp(prefix='.policy-', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(policy.encoded(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def accept(value):
    value = policy.validate(value)
    with (ROOT / 'policy.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = policy.load()
        if value['revision'] < previous['revision']:
            raise ValueError('Stale revision')
        if value['revision'] == previous['revision']:
            if policy.digest(value) != policy.digest(previous):
                raise ValueError('Revision already contains a different policy')
        else:
            write_policy(value)
    return report()


def report():
    configured = policy.load()
    result = {'protocol': policy.PROTOCOL, 'status': 'ok', 'node': 'moscow',
              'accountId': policy.ACCOUNT, 'vpnUsername': policy.USERNAME,
              'acceptedRevision': configured['revision'], 'acceptedDigest': policy.digest(configured),
              'appliedRevision': None, 'appliedDigest': None, 'state': 'pending',
              'scope': 'moscow-ikev2-eap-domain', 'bindingsCount': 0}
    try:
        status = json.loads(STATUS.read_text())
        age = time.time() - status['updated']
        command = Path('/proc') / str(int(status['pid'])) / 'cmdline'
        if not 0 <= age < 10 or str(ROOT / 'service.py').encode() not in command.read_bytes().split(b'\0'):
            return result
        if (status.get('protocol') != policy.PROTOCOL
                or status.get('policyDigest') != result['acceptedDigest']
                or status.get('policyRevision') != result['acceptedRevision']):
            return result
        result['bindingsCount'] = len(status['bindings'])
        if status.get('conflictingAddresses', 0):
            result['state'] = 'conflict'
            return result
        result.update(appliedRevision=status['policyRevision'], appliedDigest=status['policyDigest'],
                      state='applied' if status['bindings'] or not any(configured['routingRules'].values()) else 'ready')
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return result


def main():
    if os.geteuid() != 0 or len(sys.argv) != 2 or sys.argv[1] not in ('status', 'apply'):
        raise ValueError('Expected root RPC: status or apply')
    if sys.argv[1] == 'apply':
        raw = sys.stdin.buffer.read(policy.MAX_BODY + 1)
        if len(raw) > policy.MAX_BODY:
            raise ValueError('Policy too large')
        result = accept(json.loads(raw))
    else:
        result = report()
    print(json.dumps(result, separators=(',', ':')))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'protocol': policy.PROTOCOL, 'status': 'error', 'error': str(exc)}))
        sys.exit(1)
