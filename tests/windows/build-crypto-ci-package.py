"""Build a credential-free CI package with the repository's ProfileXML serializer."""
import html
import uuid
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
    # Compare provisioning transport escaping using the suite accepted by WMI.
    document = ET.fromstring(value)
    native = document.find("NativeProfile")
    minimal = ET.Element("VPNProfile")
    minimal_native = ET.SubElement(minimal, "NativeProfile")
    ET.SubElement(minimal_native, "Servers").text = "vpn-ci.invalid"
    ET.SubElement(minimal_native, "NativeProtocolType").text = "IKEv2"
    minimal_native.append(ET.fromstring(ET.tostring(native.find("CryptographySuite"))))
    minimal_native.append(ET.fromstring(ET.tostring(native.find("Authentication"))))
    minimal_value = ET.tostring(minimal, encoding="unicode")
    for level in (1, 2):
        profile_name = "TOLF-CI-PPKG-MIN-" + str(level)
        variant = destination / (profile_name + ".ppkg")
        shutil.copyfile(package, variant)
        identity = str(uuid.uuid5(uuid.NAMESPACE_URL, "tolf-ci-profilexml-" + str(level)))
        with tempfile.TemporaryDirectory(prefix="tolf-ci-transport-") as temp:
            payload = Path(temp) / "payload"
            subprocess.run([wimlib, "extract", str(variant), "1", "--dest-dir=" + str(payload)], check=True, capture_output=True)
            runtime = next(payload.rglob("*.provxml"))
            outer = ET.parse(runtime)
            target = outer.getroot().find("characteristic/characteristic")
            target.set("type", profile_name)
            target.find("parm").set("value", minimal_value if level == 1 else html.escape(minimal_value, quote=False))
            runtime.write_bytes(b'<?xml version="1.0" encoding="utf-8"?>\r\n' + ET.tostring(outer.getroot(), encoding="utf-8"))
            index_path = payload / "Multivariant/0/Prov/RunTime.xml"
            index = ET.parse(index_path)
            next(iter(index.getroot())).set("SettingsGroup", identity)
            index.write(index_path, encoding="utf-8", xml_declaration=True)
            config_path = payload / "Multivariant/0/customizations.xml"
            config = ET.parse(config_path)
            ns = "{urn:schemas-Microsoft-com:Windows-ICD-Package-Config.v1.0}"
            config.find(".//" + ns + "ID").text = "{" + identity + "}"
            config.find(".//" + ns + "Name").text = profile_name
            config.write(config_path, encoding="utf-8", xml_declaration=True)
            commands = "".join('add "' + str(item) + '" "/' + item.relative_to(payload).as_posix() + '"\n' for item in (runtime,index_path,config_path))
            subprocess.run([wimlib, "update", str(variant), "1"], input=commands, text=True, check=True, capture_output=True)
            subprocess.run([wimlib, "info", str(variant), "1", "--image-property=PACKAGEID={" + identity + "}", "--image-property=NAME=" + profile_name], check=True, capture_output=True)
            roundtrip = Path(temp) / "roundtrip"
            subprocess.run([wimlib, "extract", str(variant), "1", "--dest-dir=" + str(roundtrip)], check=True, capture_output=True)
            for item in (runtime,index_path,config_path):
                assert (roundtrip / item.relative_to(payload)).read_bytes() == item.read_bytes()
    (destination / "metadata.json").write_text(json.dumps({
        "profileName": "TOLF-CI-PPKG", "credentials": False, "connect": False,
        "scope": "CI only; not a user download or Windows 10 acceptance test"
    }, indent=2), encoding="utf-8")
    print("Credential-free CI PPKG and identical ProfileXML roundtrip verified")

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "wimlib-imagex")
