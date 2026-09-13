#!/usr/bin/python3
import base64, hashlib, json, zlib
from pathlib import Path
root = Path(__file__).resolve().parent
names = ('tolf_invite_riga.py','tolf_invitations.py')
payloads = {name:base64.b64encode(zlib.compress((root/name).read_bytes(),9)).decode() for name in names}
hashes = {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}
text = (root/'install.py').read_text().replace('PAYLOADS = {}  # Filled by build.py','PAYLOADS = '+repr(payloads)).replace('HASHES = {}','HASHES = '+repr(hashes))
(root/'install-invitations-v1.py').write_text(text)
(root/'install-invitations-v1.py.sha256').write_text(hashlib.sha256(text.encode()).hexdigest()+'  install-invitations-v1.py\n')
