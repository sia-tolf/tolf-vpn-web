from pathlib import Path
import base64, zlib, hashlib
root = Path(__file__).parent
source = (root/'install-template.py').read_text()
source = source.replace("PAYLOAD = ''", 'PAYLOAD = '+repr(base64.b64encode(zlib.compress((root/'tolf_quick.py').read_bytes(),9)).decode()))
(root/'install-quick-setup.py').write_text(source)
print(hashlib.sha256(source.encode()).hexdigest())
