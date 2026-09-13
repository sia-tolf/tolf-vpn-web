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
    for text in (root, wrapper):
        if MARKER not in text: raise RuntimeError('Install invitations v1 first; nothing changed')
    root = replace_once(root, 'if [ "${1:-}" = claim-existing ]; then',
                        'if [ "${1:-}" = claim-existing ] || [ "${1:-}" = verify-existing ]; then')
    wrapper = replace_once(wrapper, 'INVITE_PATTERN=', 'if [ "$COMMAND" = verify-existing ]; then\n    exec sudo -n /usr/local/sbin/tolf-provision-root verify-existing\nfi\nINVITE_PATTERN=')
    return root, wrapper


def london_source(source):
    if MARKER not in source or 'tolf_invitations.before_account_delete(user_id)' not in source:
        raise RuntimeError('Install invitations v1 first; nothing changed')
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
        helper = Path('/usr/local/sbin/tolf-invite')
        if hashlib.sha256(helper.read_bytes()).hexdigest() != '493afc72e11996031072d355f8a5376830a7cbf83448294ca182032b247ceb5c':
            raise RuntimeError('Riga invitation helper differs from v1; nothing changed')
        first = Path('/usr/local/sbin/tolf-provision-root')
        second = Path('/usr/local/sbin/tolf-provision-ssh')
        root,wrapper = riga_sources(first.read_text(),second.read_text())
        for content in (root,wrapper):
            subprocess.run(['bash','-n'],input=content,text=True,check=True)
        updates = {Path('/usr/local/sbin/tolf-invite'):data['tolf_invite_riga.py'],
                   first:root.encode(),second:wrapper.encode()}
        lockfile = '/var/lock/tolf-provision.lock'
    elif role == 'london':
        helper = Path('/opt/tolf-api/tolf_invitations.py')
        if hashlib.sha256(helper.read_bytes()).hexdigest() != '5b96fbaae8fbd641f3562d3646ed488879b7478a9bf296c823368e8f1306882b':
            raise RuntimeError('London invitation module differs from v1; nothing changed')
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
                            if json.load(response).get('version') != 2:
                                raise RuntimeError('Invitation endpoint is not available')
                            break
                    except Exception:
                        if attempt == 9: raise
                        time.sleep(1)
            print('OK: password linking v2 installed on '+role,flush=True)
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
