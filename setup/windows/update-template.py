#!/usr/bin/env python3
"""Update the existing TOLF Windows API on London. Built with verified payload hashes."""
import base64, fcntl, hashlib, json, os, shutil, subprocess, tempfile, time, urllib.request, zlib
from pathlib import Path
PAYLOADS = {}  # Replaced by build-update.py
HASHES = {}
EXPECTED = {'037d737bf4a7d236bf203a6fbaa5814f27792a7380adb2be1b783278ee2af850', 'a512aea770fa961d42d84cc5eef610d3af3ec2bcecadf8a70dbd3700d8c56959', '2047e0cfbeb063aa41c062ae3668f2ff2a07edb2e775e7aed7034a2c2090b5e3'}

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
    if hashlib.sha256(current).hexdigest() not in EXPECTED: raise RuntimeError('Existing Windows module differs from verified v1.0/v1.1/v1.2; nothing changed')
    payloads={name:zlib.decompress(base64.b64decode(value)) for name,value in PAYLOADS.items()}
    for name,data in payloads.items():
        if hashlib.sha256(data).hexdigest()!=HASHES[name]: raise RuntimeError('Payload checksum mismatch')
    compile(payloads['tolf_windows.py'],'tolf_windows.py','exec')
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
                with urllib.request.urlopen('https://api.tolf.is/windows/capabilities',timeout=5) as response: data=json.load(response)
                if data.get('installerVersion')=='2.0.0':
                    print('OK: Native Windows installer 2.0 enabled. Test build is unsigned.'); return
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
