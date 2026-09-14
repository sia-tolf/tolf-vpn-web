#!/usr/bin/env python3
"""Update the existing TOLF Windows API on London. Built with verified payload hashes."""
import base64, fcntl, hashlib, json, os, shutil, subprocess, tempfile, time, urllib.request, zlib
from pathlib import Path
PAYLOADS = {}  # Replaced by build-update.py
HASHES = {}
# Native 2.0: exact normalized source from commit e346834e1263484d615e152e403917a491940371.
EXPECTED = {'6e188d45c22530723151b544149c286efda791cb39629510736afaf25fb8740a', '2047e0cfbeb063aa41c062ae3668f2ff2a07edb2e775e7aed7034a2c2090b5e3', '3faefe06b19831d0b46d2a62fc694eccc4680db433c3b207c3d6cbd76d368397', '4aeb2e0a7f438b066914006171a7120854ecd8c086d1960d8a35339d9cb57ec8', '9ca05edd91cee5fc88acfcbefa770066ea8ad1dd0e8af92882aa5ead14426edf', '57feb2985016dfb57d0bf431aa694ebd1c9a6757e417f99fdd75b5ea019f6212', '3da4c567fd4befb7d53328e34dfd2c6138d21403d7e9070a0711826bb12b6314', '3a433a1842a9fee59dfee99700824659b4e332d3cabdd2cb6119a092e29fbe12', 'a512aea770fa961d42d84cc5eef610d3af3ec2bcecadf8a70dbd3700d8c56959', 'a4dec1ae9e2801b57758cdb96470bd6699df7f79cc6a11cdb72bf257b0309ba9', '9fbc3ab4fb493b4d386e29c1eac5c340ff6f22fa4fb3544521e178a010112c3c', '037d737bf4a7d236bf203a6fbaa5814f27792a7380adb2be1b783278ee2af850'}

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
    if hashlib.sha256(current.replace(b'\r\n', b'\n')).hexdigest() not in EXPECTED: raise RuntimeError('Existing Windows module differs from verified supported version; nothing changed')
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
                if data.get('installerVersion')=='2.6.0' and data.get('servers')==['riga', 'moscow'] and data.get('passwordManagement') is True:
                    print('OK: Native Windows installer 2.6.0 enabled. Test build is unsigned.'); return
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

