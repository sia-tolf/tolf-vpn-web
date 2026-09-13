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

PAYLOADS = {'tolf_invite_riga.py': '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', 'tolf_invitations.py': 'eNq1WG1T2zgQ/p5focsX2YMxAdqba24ybRpMyQFJL3H6ckzGI2yF6OpYriRTuA7//VbyS2wCNL326Eyx5dVq99ndZ1e02+1+ppY0USwkikYOElSJW3IZU0QinirGE8QXiCDBudplUmY0QhN2RRBLrpkiWsBtt9sttkq5UGhJ5DJml+Xr35In5bOg5ZP8HDNFD6vX7DIVPKRSlitZxqLWQvAVWhCpSMpQ8eHE9996NyE1hjloQj9nVKpWa+B/QD309a7lj0+9ETwK6oZ8lbKYWgJf9Hf/Irv/dHZfBLvzr88O77Dd8r3J+XDUP9PbMPhCYhYFa5+wg9cvQSZp1FyhNykTZpHEgpLoNohZ8kkvtFDtB5Mw5FmiAsAluE61WtAlgoSrYAEftIIskVmqvaNREIJOHQwSBwuwHd+1Wq2ILlDIk4SGyrK7Rj0EKRNJiaNbfgUULvDRazx3kGIryjPVO+zYhQoBWIHJgbHWMlawqND3hanl+gxEpH7pVp4I/gVggiWX3tAwU9TCU+/MG/gIgqMoOp6MzxF4F+RRkuj9iTfxUHFG7yV2UHmgY9vugqpwyRNq2eYEtjAHkCTSvy86c/RLD2FjJq7ZQJikzfhbzzovHISPWcLkEmn8WXKFbnkmEL1hUum3d29HYId+giyv5SxaMCEVLsG5pAsO2JTRimhMwcsmSA8D+GP4Qd4r2AM19ZMx3AY4f8lkARAVCJ7X1pjaMyiA+O/adEVCZTAk0UoDrgRRXOB1dq1gbxDGhK0qO5Hin2hSwAfluNL29dAF3suk2LtkyZ6US6iAXQ7/vSbg0TmPaO+WynJxkGPqF9m837lXX7rEjOBUCRaqEy7VKb0dLGmoc6GuaQY2nSb8S6Jl5DEUVw/vmIKZDN/0g9PR+P0oOBlP/SmUz+YZDDs1Ye8jCK3fZ1Nvguc7+FVdo9b1kCoD0W6VoHgHoLQ04bmz2fCoyit7B8M3A+Dc6ABargWVyixWgOWaO12RJVYBshOSFBiCBgBaCrj5IqOOojflUwnnQccJNVa9YxJLalfqgQ0zCto1fbsxJ5G08hNdqSLYmUtSk0/IqtlQBMrL2dHJFfwxHY+OaAih9YTgwkHjqXkwhQJKns7V550DyNWzorqhPuMIAX1Cyeq0hDJe0ciFTgD4mPyUZFUvdGznyQznlJWidzPgBCCvJKSWcdZBEeSPvY0pw7xZVIQDyKQ8kRSvSzHHKmdp7TfiIsfUvaLKwpo1MwmWaaLjn2osZ4R7dVm9gteRYYtchiWo7GDdRoo9Wu56m/3/Il0HGBrwIovjla7qZgt2X0ET3nf2D367A1KruapTPwGdUK3YtjVm6jYt4pNLVASlvwNhGes4j39C2IqWag4rm64hM5HPGN1y2HBQSm51TXTrKcPyBgvf3SX0BypkbjEX7IoleagNN4yBHIYj/E2CPqyZXCoxWwqCQIU+Uh/fguIjnpdm53sMjcCOwvLcNLPYDFqtKsxXB7jJBEJ/NKNVLah1cn/cjw748cB4lR8bsSuwEQwrxkZXLsnB819z1S41tWNBt1vSm1zUqvVb477i8SKAtFhxiedu2b95SoU5pzYSNZv5Fl1b/6SCXjOeyUfad26UY6Ygp0zfLVr5E528Vujl4d37PaT+sZiXcks2JbcanXQxV54+MCM9dfz+HPUeGNfuiev8MaHQsAjoBULn6GZItjf9/nRuP+x6XtVfS8rtarp11kzTrfw4mN81NNAYzP4ekx8zdeMKYN87R9JNZY1kG45gvvDRcOSP62lVJVE9C230rn8286bWSwf+2fWpsRDDKU0iIECg0OrYxmxRHwAeHOvywq/kizGg4flGZy/yANbciCrC4sc72Jal+RBU7SOoS9/7ZgWi/ugov7v0KjjajQF7s6d+D208GT7IBxiVqrP0UpmPDtz/DI8TCCcV11Q042ki+mixrFXq6F2ss7yYVTMVBkxyyOLqFQZieLVtB0OLIfie3w1oZ2+P+gBtHdWp55co5vVfcWDvpVP1aoD7HvztJ3zYtJ0lqlxd9/+5XRF6o38/Xukbisu7db5ho88XJf5f2u2PXaedn3UprCDJdwNqXT0sWXC+DQxaJn61WLs+/lJG1AhWqG+K7s/tEkczOsSxRdLUMTdGuG8UIAJ0bpZG4JxVftgGqAZEGA8mns5Av//6zEPDYzQa+8j7MIQrWwMjq5FcZfx874OP3k6G5/3JRwQXODTxjgHL0cCbGhlpQSqh8QgVFDLoTwf9I6+ZqcW8YnTp00ezszOn+CNIc3HDBjMZGJnZaPjnzHNqt22gBu+NN6l2gw3H/dmZjzo2uJ1DBai6KVxdLbwHzu6t25/cM+yMbcv8XkubIW9DuLx7WPnDt8ThIkkuWcwUo3pTTFaXEelCTgE3ST3IddH+nd36F0ssSK8='}
HASHES = {'tolf_invite_riga.py': '493afc72e11996031072d355f8a5376830a7cbf83448294ca182032b247ceb5c', 'tolf_invitations.py': '5b96fbaae8fbd641f3562d3646ed488879b7478a9bf296c823368e8f1306882b'}
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
