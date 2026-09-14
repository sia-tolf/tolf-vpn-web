#!/usr/bin/python3
"""Read-only node inventory. Never use raw-output parsing to authorize mutations."""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

VERSION = '1.0.0'
SSH = ['/usr/bin/ssh', '-n', '-i', '/root/.ssh/id_ed25519_ike_users_sync',
       '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
       '-o', 'ConnectTimeout=10', 'root@10.31.0.1']


def parse_message(text):
    tokens = re.findall(r'[^\s{}=\[\]]+|[{}=\[\]]', text)
    index = 0

    def take():
        nonlocal index
        if index >= len(tokens):
            raise ValueError('Truncated inventory')
        value = tokens[index]
        index += 1
        return value

    def section(depth=0):
        if depth > 12 or take() != '{':
            raise ValueError('Invalid inventory section')
        result = {}
        while index < len(tokens) and tokens[index] != '}':
            key = take()
            if key in '{}=[]' or key in result:
                raise ValueError('Ambiguous inventory field')
            if index < len(tokens) and tokens[index] == '{':
                result[key] = section(depth + 1)
                continue
            if take() != '=':
                raise ValueError('Invalid inventory field')
            value = take()
            if value == '[':
                value = []
                while index < len(tokens) and tokens[index] != ']':
                    item = take()
                    if item in '{}=[]':
                        raise ValueError('Invalid inventory list')
                    value.append(item)
                if take() != ']':
                    raise ValueError('Truncated inventory list')
            elif value in '{}=[]':
                raise ValueError('Invalid inventory value')
            result[key] = value
        if take() != '}':
            raise ValueError('Truncated inventory section')
        return result

    result = section()
    if index != len(tokens):
        raise ValueError('Trailing inventory data')
    return result


def number(record, key, default=None):
    value = record.get(key)
    if value is None:
        return default
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,24}', value):
        raise ValueError('Invalid inventory counter')
    return int(value)


def parse_inventory(output):
    if len(output) > 8 * 1024 * 1024:
        raise ValueError('Inventory too large')
    sessions = []
    completed = False
    seen = set()
    for line in output.splitlines():
        if not line.strip():
            continue
        if line == 'list-sas reply {}':
            if completed:
                raise ValueError('Duplicate inventory reply')
            completed = True
            continue
        if completed or not line.startswith('list-sa event '):
            raise ValueError('Unsupported inventory output')
        event = parse_message(line[len('list-sa event '):])
        if len(event) != 1:
            raise ValueError('Ambiguous inventory event')
        connection, record = next(iter(event.items()))
        if not isinstance(record, dict):
            raise ValueError('Invalid session record')
        unique_id = number(record, 'uniqueid')
        if unique_id is None or unique_id in seen:
            raise ValueError('Ambiguous session ID')
        seen.add(unique_id)
        children = record.get('child-sas', {})
        if not isinstance(children, dict) or any(not isinstance(c, dict) for c in children.values()):
            raise ValueError('Invalid child sessions')
        identity_key = 'remote-eap-id' if 'remote-eap-id' in record else 'remote-id'
        identity = record.get(identity_key)
        if identity is not None and not isinstance(identity, str):
            raise ValueError('Invalid peer identity')
        vips = record.get('remote-vips', [])
        if not isinstance(vips, list):
            raise ValueError('Invalid virtual addresses')
        sessions.append({'id': unique_id, 'connection': connection,
                         'state': record.get('state'), 'identity': identity,
                         'identitySource': identity_key, 'remoteHost': record.get('remote-host'),
                         'virtualAddresses': vips, 'establishedSeconds': number(record, 'established'),
                         'bytesIn': sum(number(c, 'bytes-in', 0) for c in children.values()),
                         'bytesOut': sum(number(c, 'bytes-out', 0) for c in children.values())})
    if not completed:
        raise ValueError('Inventory reply missing')
    return sessions


def read_node(node):
    if node not in ('riga', 'moscow'):
        raise ValueError('Invalid node')
    command = ['/usr/sbin/swanctl', '--list-sas', '--raw'] if node == 'riga' else SSH + ['swanctl --list-sas --raw']
    result = subprocess.run(command, capture_output=True, text=True, timeout=25, check=False)
    if result.returncode:
        raise RuntimeError('Node inventory command failed')
    return parse_inventory(result.stdout)


def main():
    if os.geteuid() != 0 or len(sys.argv) != 2 or sys.argv[1] not in ('riga', 'moscow'):
        print(json.dumps({'status': 'error', 'error': 'Invalid inventory request'}))
        return 1
    node = sys.argv[1]
    try:
        sessions = read_node(node)
        result = {'status': 'ok', 'version': VERSION, 'node': node, 'sessions': sessions,
                  'observedAt': datetime.now(timezone.utc).isoformat()}
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
        result = {'status': 'error', 'node': node, 'error': 'Node inventory unavailable'}
    print(json.dumps(result, ensure_ascii=True, separators=(',', ':')))
    return 0 if result['status'] == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())
