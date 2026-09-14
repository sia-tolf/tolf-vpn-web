from pathlib import Path
import base64,hashlib
root=Path(__file__).resolve().parent
data=(root/'tolf_admin.py').read_bytes()
s=(root/'install-template.py').read_text().replace("PAYLOAD = ''  # Filled by build.py",'PAYLOAD = '+repr(base64.b64encode(data).decode())).replace("PAYLOAD_SHA256 = ''",'PAYLOAD_SHA256 = '+repr(hashlib.sha256(data).hexdigest()))
(root/'install-tolf-admin.py').write_text(s)
print(hashlib.sha256(s.encode()).hexdigest()+'  install-tolf-admin.py')
