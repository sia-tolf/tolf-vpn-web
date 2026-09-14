import base64
import hashlib
from pathlib import Path
root = Path(__file__).parent
data = (root/'test_access.py').read_bytes()
text = (root/'install-access-template.py').read_text()
text = text.replace("PAYLOAD = ''", 'PAYLOAD = '+repr(base64.b64encode(data).decode()))
text = text.replace("HASH = ''", 'HASH = '+repr(hashlib.sha256(data).hexdigest()))
(root/'install-riga-test-access.py').write_text(text)
