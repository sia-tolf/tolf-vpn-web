#!/usr/bin/python3
"""Reversible credentials quarantine for Test #26 only. Root on Riga."""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile
import time
import uuid

USER = 'user_0888048cac6e44d28aed9857aa31e9ed'
CONF = Path('/etc/swanctl/conf.d/user-' + USER + '.conf')
BASE = Path('/var/lib/tolf-admin/test26-access')
STATE = BASE / 'state.json'
VAULT = BASE / 'credential.saved'
ALLOW = Path('/var/lib/ike-users/moscow-access/0888048cac6e44d28aed9857aa31e9ed.allow')
ZERO = '0' * 32
SSH = ['/usr/bin/ssh', '-T', '-i', '/root/.ssh/id_ed25519_ike_users_sync',
       '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
       '-o', 'ConnectTimeout=10', 'root@10.31.0.1']


class AccessError(Exception):
    pass


def atomic(path, data):
    fd, name = tempfile.mkstemp(prefix='.new-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(name, 0o600)
        os.replace(name, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        Path(name).unlink(missing_ok=True)


def command(args, data=None):
    result = subprocess.run(args, input=data, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, timeout=30, check=False)
    if result.returncode:
        raise AccessError('node_operation_failed')
    return result.stdout


def remote(text, data=None):
    return command(SSH + [text], data)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def remote_digest():
    output = remote("if [ -f '" + str(CONF) + "' ]; then sha256sum '" + str(CONF) + "'; else echo absent; fi").decode('ascii').split()
    if output == ['absent']:
        return None
    if len(output) != 2 or not re.fullmatch('[0-9a-f]{64}', output[0]):
        raise AccessError('invalid_node_response')
    return output[0]


def read_state():
    if not STATE.exists():
        return {'state': 'active', 'revision': ZERO}
    value = json.loads(STATE.read_text())
    if value.get('state') not in ('active', 'suspending', 'suspended', 'resuming') or not re.fullmatch('[0-9a-f]{32}', value.get('revision', '')):
        raise AccessError('invalid_saved_state')
    return value


def write_state(value):
    atomic(STATE, json.dumps(value).encode())


def report(value):
    return {'status': 'ok', 'accountNumber': 26, 'state': value['state'], 'revision': value['revision']}


def reload_local():
    command(['/usr/sbin/swanctl', '--load-creds', '--clear', '--noprompt'])


def hide_credentials():
    CONF.unlink(missing_ok=True)
    reload_local()
    remote("rm -f '" + str(CONF) + "' && swanctl --load-creds --clear --noprompt >/dev/null 2>&1")


def restore_credentials(data):
    if not ALLOW.is_file():
        raise AccessError('moscow_permission_missing')
    if CONF.exists() and digest(CONF.read_bytes()) != digest(data):
        raise AccessError('local_credential_conflict')
    remote_hash = remote_digest()
    if remote_hash not in (None, digest(data)):
        raise AccessError('remote_credential_conflict')
    # Secret bytes travel only through SSH stdin, never argv, logs or JSON.
    remote("set -eu; umask 077; tmp=$(mktemp /etc/swanctl/conf.d/.test26.XXXXXX); "
           "trap 'rm -f \"$tmp\"' EXIT; cat >\"$tmp\"; chmod 600 \"$tmp\"; "
           "mv -f \"$tmp\" '" + str(CONF) + "'; swanctl --load-creds --clear --noprompt >/dev/null 2>&1", data)
    atomic(CONF, data)
    reload_local()
    if remote_digest() != digest(data):
        raise AccessError('restoration_not_confirmed')


def terminate_test_sessions():
    bridge = runpy.run_path('/usr/local/sbin/tolf-admin-test-control')
    deadline = time.monotonic() + 60
    for node in ('riga', 'moscow'):
        # Re-list once per selected SA so each operation has a fresh bounded transport.
        for attempt in range(16):
            if time.monotonic() >= deadline:
                raise AccessError('test_disconnect_timeout')
            with bridge['connect'](node) as client:
                client.deadline = min(client.deadline, deadline)
                inventory = client.inventory()
                if any(row.get('remote-id') == USER.encode() and row.get('remote-eap-id') != USER.encode() for row in inventory):
                    raise AccessError('test_session_identity_not_verifiable')
                selected = [bridge['selector'](row) for row in inventory
                            if row.get('remote-eap-id') == USER.encode()]
                if any(item is None for item in selected):
                    raise AccessError('test_authentication_in_progress')
                if not selected:
                    break
                result = bridge['operate'](client, selected[0])
                if result.get('status') != 'ok':
                    raise AccessError('test_disconnect_not_confirmed')
        else:
            raise AccessError('test_sessions_remain')


def change(action, expected):
    value = read_state()
    if value['revision'] != expected:
        raise AccessError('stale_revision')
    if action == 'suspend':
        if value['state'] == 'active':
            if not CONF.is_file() or not ALLOW.is_file():
                raise AccessError('test_credentials_or_permission_missing')
            data = CONF.read_bytes()
            # Never overwrite a different Moscow credential on later resume.
            if remote_digest() != digest(data):
                raise AccessError('node_credentials_differ')
            atomic(VAULT, data)
            value['digest'] = digest(data)
        elif not VAULT.is_file() or digest(VAULT.read_bytes()) != value.get('digest'):
            raise AccessError('saved_credential_invalid')
        value.update(state='suspending', revision=uuid.uuid4().hex)
        write_state(value)  # durable deny gate BEFORE removing either credential
        hide_credentials()
        terminate_test_sessions()
        if CONF.exists() or remote_digest() is not None:
            raise AccessError('suspension_not_confirmed')
        value['state'] = 'suspended'
        write_state(value)
    elif action == 'resume':
        if value['state'] == 'active':
            return report(value)
        if not VAULT.is_file() or digest(VAULT.read_bytes()) != value.get('digest'):
            raise AccessError('saved_credential_invalid')
        value.update(state='resuming', revision=uuid.uuid4().hex)
        write_state(value)
        restore_credentials(VAULT.read_bytes())
        value['state'] = 'active'
        write_state(value)  # allow synchronisation only AFTER both reloads succeed
        VAULT.unlink(missing_ok=True)
    else:
        raise AccessError('invalid_action')
    return report(value)


def guard(username):
    if username == USER and read_state()['state'] != 'active':
        raise AccessError('test_access_suspended')


def main():
    if os.geteuid() != 0:
        raise AccessError('root_required')
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == 'guard':
        guard(args[1])
        return
    if args != ['status'] and (len(args) != 2 or args[0] not in ('suspend', 'resume') or not re.fullmatch('[0-9a-f]{32}', args[1])):
        raise AccessError('invalid_arguments')
    BASE.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(BASE, 0o700)
    with contextlib.ExitStack() as stack:
        # Same order as provision-root -> sync. Guard mode never reacquires locks.
        for filename in ('/var/lock/tolf-provision.lock', '/var/lock/tolf-admin-test-sync.lock'):
            lock = stack.enter_context(open(filename, 'a'))
            fcntl.flock(lock, fcntl.LOCK_EX)
        result = report(read_state()) if args == ['status'] else change(*args)
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # A partial operation remains durably suspending/resuming; never claim success.
        print(json.dumps({'status': 'error', 'error': str(exc) if isinstance(exc, AccessError) else 'access_operation_failed'}))
        sys.exit(1)
