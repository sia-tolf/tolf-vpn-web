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
template = (directory / "install-moscow-devices.template.sh").read_text()
for marker, name in (("# BUILD_DEVICES_SCRIPT", "moscow-devices.sh"),
                     ("# BUILD_REMOTE_SCRIPT", "moscow-remote.sh")):
    assert template.count(marker) == 1
    template = template.replace(marker, (directory / name).read_text().rstrip())
(directory / "install-moscow-devices.sh").write_text(template)
print("Moscow devices:", hashlib.sha256(template.encode()).hexdigest())
template = (directory / "install-riga-foundation.template.py").read_text()
sync = (directory / "sync-moscow-crl.sh").read_text()
sync = sync.replace('/etc/ocserv-moscow', '/etc/ocserv/tolf-uk')
sync = sync.replace('/var/run/occtl-moscow.socket', '/run/occtl.socket')
sync = sync.replace('/tmp/tolf-oc-crl-sync.lock', '/run/tolf-oc-riga-crl-sync.lock')
sync = sync.replace('/tmp/tolf-oc-crl-last-sync', '/run/tolf-oc-riga-crl-last-sync')
assert template.count('SYNC = ""  # BUILD_RIGA_SYNC') == 1
output = template.replace('SYNC = ""  # BUILD_RIGA_SYNC', 'SYNC = ' + repr(sync))
compile(output, 'install-riga-foundation.py', 'exec')
(directory / 'install-riga-foundation.py').write_text(output)
print('Riga foundation:', hashlib.sha256(output.encode()).hexdigest())
payload = {}
for name in ('riga-devices.py', 'riga-remote.py'):
    data = (directory / name).read_bytes()
    payload[name] = {'sha256': hashlib.sha256(data).hexdigest(),
                     'data': base64.b64encode(data).decode('ascii')}
template = (directory / 'install-riga-devices.template.py').read_text()
assert template.count('PAYLOAD = {}  # BUILD_RIGA_DEVICES') == 1
output = template.replace('PAYLOAD = {}  # BUILD_RIGA_DEVICES', 'PAYLOAD = ' + repr(payload))
compile(output, 'install-riga-devices.py', 'exec')
(directory / 'install-riga-devices.py').write_text(output)
print('Riga devices:', hashlib.sha256(output.encode()).hexdigest())
