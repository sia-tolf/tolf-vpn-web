"""Isolated certificate-only EAP-TLS PPKG feasibility test; never production."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
NS = {v: "http://www.microsoft.com/provisioning/" + k for v, k in {
    "host": "EapHostConfig", "common": "EapCommon",
    "base": "BaseEapConnectionPropertiesV1", "tls1": "EapTlsConnectionPropertiesV1",
    "tls2": "EapTlsConnectionPropertiesV2", "tls3": "EapTlsConnectionPropertiesV3"}.items()}
CLIENT_CA = "11" * 20
SERVER_CA = "22" * 20

def add(parent, namespace, name, value=None, **attributes):
    child = ET.SubElement(parent, "{" + NS[namespace] + "}" + name, attributes)
    child.text = value
    return child

def eap_config(device):
    host = ET.Element("{" + NS["host"] + "}EapHostConfig")
    method = add(host, "host", "EapMethod")
    for key, value in (("Type", "13"), ("VendorId", "0"), ("VendorType", "0"), ("AuthorId", "0")):
        add(method, "common", key, value)
    eap = add(add(host, "host", "Config"), "base", "Eap")
    add(eap, "base", "Type", "13")
    tls = add(eap, "tls1", "EapType")
    store = add(add(tls, "tls1", "CredentialsSource"), "tls1", "CertificateStore")
    add(store, "tls1", "SimpleCertSelection", "true")
    server = add(tls, "tls1", "ServerValidation")
    add(server, "tls1", "DisableUserPromptForServerValidation", "true")
    add(server, "tls1", "ServerNames", "vpn-ci.invalid")
    add(server, "tls1", "TrustedRootCA", SERVER_CA)
    add(tls, "tls1", "DifferentUsername", "false")
    add(tls, "tls2", "PerformServerValidation", "true")
    add(tls, "tls2", "AcceptServerName", "true")
    filters = add(add(tls, "tls2", "TLSExtensions"), "tls3", "FilteringInfo")
    add(filters, "tls3", "AllPurposeEnabled", "false")
    add(add(filters, "tls3", "CAHashList", Enabled="true"), "tls3", "IssuerHash", CLIENT_CA)
    mapping = add(add(filters, "tls3", "EKUMapping"), "tls3", "EKUMap")
    add(mapping, "tls3", "EKUName", "TOLF-CI-Device")
    add(mapping, "tls3", "EKUOID", "1.3.6.1.4.1.32473.1." + ".".join(str(int.from_bytes(uuid.UUID(device).bytes[i:i+2], "big")) for i in range(0,16,2)))
    allowed = add(filters, "tls3", "ClientAuthEKUList", Enabled="true")
    add(add(allowed, "tls3", "EKUMapInList"), "tls3", "EKUName", "TOLF-CI-Device")
    add(filters, "tls3", "AnyPurposeEKUList", Enabled="false")
    return host

def build(destination, wimlib):
    destination = Path(destination)
    spec = importlib.util.spec_from_file_location("crypto_ci", ROOT / "tests/windows/build-crypto-ci-package.py")
    crypto = importlib.util.module_from_spec(spec); spec.loader.exec_module(crypto)
    crypto.build(destination, wimlib)
    devices = ("00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002")
    for index, device in enumerate(devices, 1):
        (destination / ("Eap-" + str(index) + ".xml")).write_bytes(ET.tostring(eap_config(device)))
    package = destination / "TOLF-CI-Crypto.ppkg"
    with tempfile.TemporaryDirectory(prefix="tolf-ci-eaptls-") as tmp:
        payload = Path(tmp) / "payload"
        subprocess.run([wimlib, "extract", str(package), "1", "--dest-dir=" + str(payload)], check=True, capture_output=True)
        runtime = next(payload.rglob("*.provxml"))
        outer = ET.parse(runtime)
        parm = outer.getroot().find("characteristic/characteristic/parm")
        profile = ET.fromstring(parm.get("value"))
        native = profile.find("NativeProfile")
        native.find("Servers").text = "vpn-ci.invalid"
        auth = native.find("Authentication")
        auth.clear()
        ET.SubElement(auth, "UserMethod").text = "Eap"
        ET.SubElement(ET.SubElement(auth, "Eap"), "Configuration").append(eap_config(devices[0]))
        value = ET.tostring(profile, encoding="unicode")
        parm.set("value", value)
        (destination / "ProfileXML.xml").write_text(value, encoding="utf-8")
        runtime.write_bytes(b'\xef\xbb\xbf<?xml version="1.0" encoding="utf-8"?>\r\n' + ET.tostring(outer.getroot()))
        command = 'add "' + str(runtime) + '" "/' + runtime.relative_to(payload).as_posix() + '"\n'
        subprocess.run([wimlib, "update", str(package), "1"], input=command, text=True, check=True, capture_output=True)
        restored = Path(tmp) / "restored"
        subprocess.run([wimlib, "extract", str(package), "1", "--dest-dir=" + str(restored)], check=True, capture_output=True)
        if (restored / runtime.relative_to(payload)).read_bytes() != runtime.read_bytes():
            raise ValueError("EAP-TLS PPKG roundtrip failed")
    for item in destination.glob("TOLF-CI-PPKG-MIN-*.ppkg"):
        item.unlink()
    (destination / "eaptls-metadata.json").write_text(json.dumps({
        "certificateOnly": True, "credentials": False, "connect": False,
        "clientCA": CLIENT_CA, "serverCA": SERVER_CA,
        "devices": list(devices), "status": "CI prototype; not production or handshake acceptance"
    }, indent=2))
    print("EAP-TLS XML and PPKG roundtrip verified; no credentials or live server target")

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "wimlib-imagex")
