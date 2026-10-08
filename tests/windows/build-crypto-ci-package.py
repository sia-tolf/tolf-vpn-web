"""Build a credential-free CI package with the repository's ProfileXML serializer."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ci_personalize", ROOT / "setup/windows/ppkg/personalize.py")
personalize = importlib.util.module_from_spec(spec)
spec.loader.exec_module(personalize)

def build(destination, wimlib="wimlib-imagex"):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    package = destination / "TOLF-CI-Crypto.ppkg"
    shutil.copyfile(ROOT / "setup/windows/ppkg/diagnostic/TOLF-Crypto-Check.ppkg", package)
    with tempfile.TemporaryDirectory(prefix="tolf-ci-crypto-") as temp:
        payload = Path(temp) / "payload"
        subprocess.run([wimlib, "extract", str(package), "1", "--dest-dir=" + str(payload)], check=True, capture_output=True)
        runtimes = list(payload.rglob("*.provxml"))
        if len(runtimes) != 1:
            raise ValueError("CI template must contain only the VPN runtime")
        index = ET.parse(payload / "Multivariant/0/Prov/RunTime.xml")
        if len(list(index.getroot())) != 1:
            raise ValueError("CI template has unexpected runtime groups")
        runtime = runtimes[0]
        personalize.preserve_local_routes(runtime)
        personalize.use_profile_xml(runtime)
        outer = ET.parse(runtime)
        provider = outer.getroot().find("characteristic")
        if provider.get("type") != "VPNv2" or len(list(outer.getroot())) != 1:
            raise ValueError("CI runtime has a non-VPN provider")
        target = provider.find("characteristic")
        target.set("type", "TOLF-CI-PPKG")
        value = target.find("parm").get("value")
        if target.find("parm").get("name") != "ProfileXML" or len(list(target)) != 1:
            raise ValueError("CI runtime must contain only ProfileXML")
        (destination / "ProfileXML.xml").write_text(value, encoding="utf-8")
        # The native outer XML escapes the ProfileXML value once.
        runtime.write_bytes(b'<?xml version="1.0" encoding="utf-8"?>\r\n' + ET.tostring(outer.getroot(), encoding="utf-8"))
        relative = "/" + runtime.relative_to(payload).as_posix()
        command = 'add "' + str(runtime) + '" "' + relative + '"\n'
        subprocess.run([wimlib, "update", str(package), "1"], input=command, text=True, check=True, capture_output=True)
        roundtrip = Path(temp) / "roundtrip"
        subprocess.run([wimlib, "extract", str(package), "1", "--dest-dir=" + str(roundtrip)], check=True, capture_output=True)
        restored = roundtrip / runtime.relative_to(payload)
        assert restored.read_bytes() == runtime.read_bytes()
        assert len(list(roundtrip.rglob("*.provxml"))) == 1
        assert all(p.suffix.lower() in {".xml", ".provxml"} for p in roundtrip.rglob("*") if p.is_file())
    (destination / "metadata.json").write_text(json.dumps({
        "profileName": "TOLF-CI-PPKG", "credentials": False, "connect": False,
        "scope": "CI only; not a user download or Windows 10 acceptance test"
    }, indent=2), encoding="utf-8")
    print("Credential-free CI PPKG and identical ProfileXML roundtrip verified")

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "wimlib-imagex")
