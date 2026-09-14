import base64
import hashlib
from pathlib import Path

root = Path(__file__).parent
data = (root/'session_reader.py').read_bytes()
template = (root/'install-template.py').read_text()
template = template.replace("PAYLOAD = ''", 'PAYLOAD = '+repr(base64.b64encode(data).decode()))
template = template.replace("HASH = ''", 'HASH = '+repr(hashlib.sha256(data).hexdigest()))
(root/'install-riga-sessions.py').write_text(template)
