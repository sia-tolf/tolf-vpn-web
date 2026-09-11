from pathlib import Path
import base64,hashlib,zlib
root=Path(__file__).resolve().parent
payloads={'tolf_windows.py':(root/'tolf_windows.py').read_bytes(),'TOLF-Setup.exe':(root/'dist/TOLF-Setup.exe').read_bytes()}
s=(root/'update-template.py').read_text()
s=s.replace('PAYLOADS = {}  # Replaced by build-update.py','PAYLOADS = '+repr({name:base64.b64encode(zlib.compress(data,9)).decode() for name,data in payloads.items()}))
s=s.replace('HASHES = {}','HASHES = '+repr({name:hashlib.sha256(data).hexdigest() for name,data in payloads.items()}))
(root/'dist/update-windows-gui.py').write_text(s,encoding='utf-8')
with (root/'dist/SHA256SUMS').open('w') as f:
 for name in ['TOLF-Setup.exe','update-windows-gui.py']:
  f.write(hashlib.sha256((root/'dist'/name).read_bytes()).hexdigest()+'  '+name+'\n')
