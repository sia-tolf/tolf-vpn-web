#!/usr/bin/python3
"""Guarded two-host installer. Run the packaged version as root."""
import ast
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zlib

PAYLOADS = {}  # Filled by build.py
HASHES = {}
MARKER = '# TOLF existing VPN invitations v1'


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError('Unexpected server source at: '+old[:100]+'; nothing changed')
    return text.replace(old,new,1)


def riga_sources(root, wrapper):
    if MARKER in root or MARKER in wrapper:
        raise RuntimeError('Invitation update already installed; nothing changed')
    root = replace_once(root, "DIR='/etc/swanctl/conf.d'", MARKER+'''
if [ "${1:-}" = claim-existing ]; then
    exec /usr/local/sbin/tolf-invite "$@"
fi
DIR='/etc/swanctl/conf.d' ''').replace("DIR='/etc/swanctl/conf.d' \n", "DIR='/etc/swanctl/conf.d'\n")
    anchor = 'ACCESS_FILE="$ACCESS_DIR/$COMPACT.allow"'
    root = replace_once(root, anchor, anchor+'''
BOUND_USER="$(/usr/local/sbin/tolf-invite resolve "$ACCOUNT_ID")"
if [ -n "$BOUND_USER" ]; then
    [[ "$BOUND_USER" =~ ^[A-Za-z0-9_.@-]{1,128}$ ]] || fail 'invalid linked username'
    NEW_USER="$BOUND_USER"
    LEGACY_USER="$BOUND_USER"
    NEW_FILE="$DIR/user-${BOUND_USER}.conf"
    LEGACY_FILE="$NEW_FILE"
    case "$BOUND_USER:$ACTION" in
        user0:delete|user0_ipad:delete|user0:revoke-moscow|user0_ipad:revoke-moscow)
            fail 'protected VPN user' ;;
    esac
fi
''')
    # Username-only operations have no UUID and must retain their original semantics.
    root = replace_once(root, 'BOUND_USER="$(/usr/local/sbin/tolf-invite resolve "$ACCOUNT_ID")"', '''BOUND_USER=""
case "$ACTION" in
    create-username|delete-username) ;;
    *) BOUND_USER="$(/usr/local/sbin/tolf-invite resolve "$ACCOUNT_ID")" ;;
esac''')
    root = replace_once(root, '        if ! find_user; then\n            prepare_identity', '''        if ! find_user; then
            case "$BOUND_USER" in user0|user0_ipad) fail 'protected VPN user' ;; esac
            prepare_identity''')
    root = replace_once(root, '        echo \'{"status":"ok","moscowEnabled":false}\'', '        [ -z "$BOUND_USER" ] || /usr/local/sbin/tolf-invite release "$ACCOUNT_ID"\n        echo \'{"status":"ok","moscowEnabled":false}\'')
    wrapper = replace_once(wrapper, 'if [[ "$COMMAND" =~ $USERNAME_ACTION_PATTERN ]]; then', MARKER+'''
INVITE_PATTERN="^claim-existing[[:space:]]+($UUID_PATTERN)[[:space:]]+([A-Za-z0-9_-]{43})$"
if [[ "$COMMAND" =~ $INVITE_PATTERN ]]; then
    exec sudo -n /usr/local/sbin/tolf-provision-root claim-existing "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
fi

if [[ "$COMMAND" =~ $USERNAME_ACTION_PATTERN ]]; then''')
    return root, wrapper


def london_source(source):
    if MARKER in source:
        raise RuntimeError('Invitation update already installed; nothing changed')
    tree = ast.parse(source)
    funcs = {n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    for name in ('provision_on_riga','account_delete','vpn_record','authenticated_user_id','utc_iso','utc_now'):
        if name not in funcs: raise RuntimeError('Missing API function: '+name)
    source = replace_once(source, 'def provision_on_riga(action, user_id, server="riga", local_id=None):',
                          'def provision_on_riga(action, user_id, server="riga", local_id=None):\n    tolf_invitations.require_ready(user_id)')
    source = replace_once(source, '        tolf_windows.delete_all(user_id)',
                          '        tolf_invitations.before_account_delete(user_id)\n        tolf_windows.delete_all(user_id)')
    source = replace_once(source, '("windows_devices", "vpn_access", "passkeys", "sessions")',
                          '("windows_devices", "vpn_imports", "vpn_access", "passkeys", "sessions")')
    source += '\n\n'+MARKER+'\nimport tolf_invitations\ntolf_invitations.install(app, globals())\n'
    compile(source,'main.py','exec')
    return source


def atomic(path, data, mode, uid=0, gid=0):
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.tolf-invite-')
    try:
        with os.fdopen(fd,'wb') as out:
            os.fchmod(out.fileno(),mode)
            os.fchown(out.fileno(),uid,gid)
            out.write(data); out.flush(); os.fsync(out.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)


def main(role):
    if os.geteuid() != 0: raise RuntimeError('Run as root')
    data = {name:zlib.decompress(base64.b64decode(value)) for name,value in PAYLOADS.items()}
    for name,value in data.items():
        if hashlib.sha256(value).hexdigest() != HASHES[name]: raise RuntimeError('Payload checksum mismatch')
        compile(value,name,'exec')
    if role == 'riga':
        first = Path('/usr/local/sbin/tolf-provision-root')
        second = Path('/usr/local/sbin/tolf-provision-ssh')
        root,wrapper = riga_sources(first.read_text(),second.read_text())
        for content in (root,wrapper):
            subprocess.run(['bash','-n'],input=content,text=True,check=True)
        updates = {Path('/usr/local/sbin/tolf-invite'):data['tolf_invite_riga.py'],
                   first:root.encode(),second:wrapper.encode()}
        lockfile = '/var/lock/tolf-provision.lock'
    elif role == 'london':
        first = Path('/opt/tolf-api/main.py')
        source = london_source(first.read_text())
        updates = {Path('/opt/tolf-api/tolf_invitations.py'):data['tolf_invitations.py'],first:source.encode()}
        lockfile = '/var/lock/tolf-invitations-install.lock'
    else:
        raise RuntimeError('Usage: installer.py riga|london')
    backup = Path(tempfile.mkdtemp(prefix='tolf-invitations-backup-',dir='/root'))
    info = first.stat()
    print('Backup:',backup,flush=True)
    with open(lockfile,'a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        for path in updates:
            if path.exists(): shutil.copy2(path,backup/path.name)
        try:
            for path,value in updates.items():
                old = path.stat() if path.exists() else info
                atomic(path,value,0o755 if role=='riga' else 0o644,old.st_uid,old.st_gid)
            if role == 'london':
                subprocess.run(['systemctl','restart','tolf-api.service'],check=True)
                for attempt in range(10):
                    try:
                        with urllib.request.urlopen('https://api.tolf.is/vpn/invitations/capabilities',timeout=5) as response:
                            if json.load(response).get('version') != 1:
                                raise RuntimeError('Invitation endpoint is not available')
                            break
                    except Exception:
                        if attempt == 9: raise
                        time.sleep(1)
            print('OK: invitations installed on '+role,flush=True)
        except Exception:
            for path in updates:
                saved = backup/path.name
                if saved.exists():
                    old = saved.stat()
                    atomic(path,saved.read_bytes(),old.st_mode & 0o777,old.st_uid,old.st_gid)
                else: path.unlink(missing_ok=True)
            if role == 'london': subprocess.run(['systemctl','restart','tolf-api.service'],check=False)
            print('Previous files restored; backup:',backup)
            raise

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv)==2 else '')
