#!/usr/bin/env python3
"""Update the existing TOLF Windows API on London. Built with verified payload hashes."""
import base64, fcntl, hashlib, json, os, shutil, subprocess, tempfile, time, urllib.request, zlib
from pathlib import Path
PAYLOADS = {}  # Replaced by build-update.py
HASHES = {}
# Native 2.0: exact normalized source from commit e346834e1263484d615e152e403917a491940371.
EXPECTED = {'46b9abf385fac997cc170f962e57575dc55f4d901d977b9649f209946119646d'}

def write(path, data, info):
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.tolf-update-')
    try:
        with os.fdopen(fd,'wb') as f:
            os.fchmod(f.fileno(),0o644)
            os.fchown(f.fileno(),info.st_uid,info.st_gid)
            f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp): os.unlink(temp)

def main():
    root=Path('/opt/tolf-api'); module=root/'tolf_windows.py'
    if os.geteuid()!=0 or not module.is_file(): raise RuntimeError('Run on London EDISUK, where Windows API v1 is installed')
    current=module.read_bytes()
    if hashlib.sha256(current.replace(b'\r\n', b'\n')).hexdigest() not in (EXPECTED | {HASHES.get('tolf_windows.py')}): raise RuntimeError('Existing Windows module differs from verified supported version; nothing changed')
    payloads={name:zlib.decompress(base64.b64decode(value)) for name,value in PAYLOADS.items()}
    for name,data in payloads.items():
        if hashlib.sha256(data).hexdigest()!=HASHES[name]: raise RuntimeError('Payload checksum mismatch')
    for name, data in payloads.items():
        if name.endswith('.py'): compile(data, name, 'exec')
    if not payloads['TOLF-Setup.exe'].startswith(b'MZ'): raise RuntimeError('Invalid Windows executable')
    backup=Path('/root/tolf-windows-gui-backup-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid()))
    backup.mkdir(mode=0o700)
    for name in payloads:
        if (root/name).exists(): shutil.copy2(root/name,backup/name)
    print('Backup:',backup,flush=True)
    info=module.stat()
    try:
        for name,data in payloads.items(): write(root/name,data,info)
        subprocess.run(['systemctl','restart','tolf-api.service'],check=True)
        for i in range(12):
            try:
                with urllib.request.urlopen('http://127.0.0.1:8000/windows/capabilities',timeout=5) as response: data=json.load(response)
                if data.get('installerVersion')=='2.6.1' and data.get('profileLabels') is True and data.get('passwordManagement') is True and data.get('routingRevision')=='windows-routing-2.6-v1':
                    print('OK: Windows 2.6.1 enabled: profile names, entry points and routing modes; passwords and routing preserved.'); return
            except Exception: pass
            time.sleep(2)
        raise RuntimeError('API health check failed')
    except Exception:
        for name in payloads:
            old=backup/name
            if old.exists(): write(root/name,old.read_bytes(),info)
            else: (root/name).unlink(missing_ok=True)
        subprocess.run(['systemctl','restart','tolf-api.service'],check=False)
        print('Previous API restored; backup:',backup)
        raise
if __name__=='__main__':
    with open('/var/lock/tolf-windows-install.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);main()

