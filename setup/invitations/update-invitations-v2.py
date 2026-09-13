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

PAYLOADS = {'tolf_invite_riga.py': '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', 'tolf_invitations.py': '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'}
HASHES = {'tolf_invite_riga.py': '0758d7e5dac905d6a8e1aa3b574a497671dc3a9e18ece10c9cb400f08b7a5f90', 'tolf_invitations.py': '0cd6621af1057b98825bfc2992cb5a71c2468e1aa59419be95ff72e8d1c67bc4'}
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
