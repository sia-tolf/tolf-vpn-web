from pathlib import Path
import base64
import zlib
root=Path(__file__).resolve().parent
payload=base64.b64encode(zlib.compress((root/'tolf_password_auth.py').read_bytes(),9)).decode()
source=(root/'install-template.py').read_text().replace("PAYLOAD = ''", 'PAYLOAD = '+repr(payload))
(root/'install-password-auth.py').write_text(source)
