"""Build a self-contained UK installer; never embeds live credentials or certificates."""
import base64
import hashlib
import json
from pathlib import Path

directory = Path(__file__).resolve().parent
payload = {}
for name in ("tolf_oc_certificates.py", "tolf_anyconnect.py"):
    data = (directory / name).read_bytes()
    payload[name] = {"sha256": hashlib.sha256(data).hexdigest(),
                     "data": base64.b64encode(data).decode("ascii")}
template = (directory / "install-template.py").read_text()
assert template.count("PAYLOAD = {}  # BUILD_PAYLOAD") == 1
output = template.replace("PAYLOAD = {}  # BUILD_PAYLOAD",
                          "PAYLOAD = " + repr(payload))
compile(output, "install-uk-foundation.py", "exec")
(directory / "install-uk-foundation.py").write_text(output)
print(hashlib.sha256(output.encode()).hexdigest())
template = (directory / "install-moscow-crl.template.sh").read_text()
assert template.count("# BUILD_SYNC_SCRIPT") == 1
output = template.replace("# BUILD_SYNC_SCRIPT", (directory / "sync-moscow-crl.sh").read_text().rstrip())
(directory / "install-moscow-crl.sh").write_text(output)
print("Moscow CRL:", hashlib.sha256(output.encode()).hexdigest())
