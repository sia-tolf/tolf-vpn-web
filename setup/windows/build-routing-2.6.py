from pathlib import Path
import base64,hashlib,zlib
root=Path(__file__).resolve().parents[2]
payloads={'tolf_windows.py':(root/'setup/windows/compat-2.6/tolf_windows.py').read_bytes(), 'tolf_windows_routes.py':(root/'setup/windows/tolf_windows_routes.py').read_bytes()}
header='''#!/usr/bin/env python3
"""London API-only routing update for the verified deployed Windows 2.6 module.
Does not replace TOLF-Setup.exe or the legacy PowerShell template.
"""
import base64,fcntl,hashlib,json,os,sqlite3,subprocess,tempfile,time,urllib.request,zlib
from pathlib import Path
'''
header+='PAYLOADS = '+repr({n:base64.b64encode(zlib.compress(v,9)).decode() for n,v in payloads.items()})+'\n'
header+='HASHES = '+repr({n:hashlib.sha256(v).hexdigest() for n,v in payloads.items()})+'\n'
header+='EXPECTED = '+repr({'3a433a1842a9fee59dfee99700824659b4e332d3cabdd2cb6119a092e29fbe12',hashlib.sha256(payloads['tolf_windows.py']).hexdigest()})+'\n'
header+='''

def write(path,data,info):
    fd,temp=tempfile.mkstemp(dir=path.parent,prefix='.tolf-routing-')
    try:
        with os.fdopen(fd,'wb') as f:
            os.fchmod(f.fileno(),info.st_mode & 0o777)
            os.fchown(f.fileno(),info.st_uid,info.st_gid)
            f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def main():
    root=Path('/opt/tolf-api');module=root/'tolf_windows.py';exe=root/'TOLF-Setup.exe'
    if os.geteuid()!=0 or not module.is_file():raise RuntimeError('Run on London EDISUK as root')
    current=module.read_bytes()
    if hashlib.sha256(current.replace(b'\\r\\n',b'\\n')).hexdigest() not in EXPECTED:
        raise RuntimeError('Windows API differs from verified 2.6 source; nothing changed')
    executable_hash=hashlib.sha256(exe.read_bytes()).hexdigest()
    payloads={n:zlib.decompress(base64.b64decode(v)) for n,v in PAYLOADS.items()}
    if set(payloads)!={'tolf_windows.py','tolf_windows_routes.py'}:raise RuntimeError('Invalid payload targets')
    for name,data in payloads.items():
        if hashlib.sha256(data).hexdigest()!=HASHES[name]:raise RuntimeError('Payload checksum mismatch')
        compile(data,name,'exec')
    backup=Path(tempfile.mkdtemp(prefix='tolf-windows-routing-26-backup-',dir='/root'))
    originals={name:(root/name).read_bytes() if (root/name).exists() else None for name in payloads}
    info=module.stat()
    for name,data in originals.items():
        if data is not None:(backup/name).write_bytes(data)
    db=Path('/var/lib/tolf-api/tolf.db')
    if db.is_file():
        with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as src,sqlite3.connect(backup/'tolf.db') as dst:src.backup(dst)
    print('Backup:',backup,flush=True)
    try:
        for name in ('tolf_windows_routes.py','tolf_windows.py'):write(root/name,payloads[name],info)
        subprocess.run(['systemctl','restart','tolf-api.service'],check=True)
        for attempt in range(12):
            try:
                with urllib.request.urlopen('http://127.0.0.1:8000/windows/capabilities',timeout=8) as response:state=json.load(response)
                if state.get('routingRevision')=='windows-routing-2.6-v1' and state.get('installerVersion')=='2.6.0' and state.get('passwordManagement') is True:
                    if hashlib.sha256(exe.read_bytes()).hexdigest()!=executable_hash:raise RuntimeError('Windows executable changed during update')
                    print('OK: Windows routing API installed on London; installer 2.6 and password management preserved.')
                    print('Routing modes:',json.dumps(state.get('routingModes')))
                    return
            except (OSError,ValueError):pass
            time.sleep(2)
        raise RuntimeError('API health check failed')
    except Exception:
        for name,data in originals.items():
            if data is None:(root/name).unlink(missing_ok=True)
            else:write(root/name,data,info)
        subprocess.run(['systemctl','restart','tolf-api.service'],check=False)
        print('Previous API restored; Windows executable was not replaced.')
        raise

if __name__=='__main__':
    with open('/var/lock/tolf-windows-install.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);main()
'''
(root/'setup/windows/update-routing-2.6.py').write_text(header)
