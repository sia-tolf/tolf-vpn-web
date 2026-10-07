"""Validate native runtime settings extracted from the compiled PPKG."""
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

CRYPTO = {
    "AuthenticationTransformConstants": "SHA256128",
    "CipherTransformConstants": "AES256",
    "PfsGroup": "None",
    "DHGroup": "Group14",
    "IntegrityCheckMethod": "SHA256",
    "EncryptionMethod": "AES256",
}

def runtime_settings(root):
    settings = {}
    def walk(node, path=()):
        if node.tag == "characteristic":
            path += (node.get("type"),)
        if node.tag == "parm":
            key = path + (node.get("name"),)
            value = node.get("value")
            if key in settings and settings[key] != value:
                raise ValueError("Conflicting runtime setting")
            settings[key] = value
        for child in node:
            walk(child, path)
    for path in root.rglob("*.provxml"):
        walk(ET.parse(path).getroot())
    return settings

def verify(root):
    files = [p for p in root.rglob("*") if p.is_file()]
    if not files:
        raise ValueError("Empty extracted package")
    for path in files:
        if path.suffix.lower() in {".exe", ".dll", ".ps1", ".cmd", ".bat", ".vbs", ".js", ".msi"}:
            raise ValueError("Executable payload found: " + path.name)
    settings = runtime_settings(root)
    profiles = {key[:2] for key in settings if len(key) >= 2 and key[0] == "VPNv2"}
    if len(profiles) != 1 or any(key[0] != "VPNv2" for key in settings):
        raise ValueError("Expected exactly one native VPN profile and no other runtime providers")
    prefix = next(iter(profiles))
    expected = {("NativeProfile", "CryptographySuite", k): v for k, v in CRYPTO.items()}
    expected.update({
        ("NativeProfile", "NativeProtocolType"): "Ikev2",
        ("NativeProfile", "Authentication", "UserMethod"): "Eap",
        ("NativeProfile", "RoutingPolicyType"): "ForceTunnel",
        ("AlwaysOn",): "false",
        ("RememberCredentials",): "true",
    })
    for suffix, value in expected.items():
        if settings.get(prefix + suffix) != value:
            raise ValueError("Wrong or missing runtime setting: " + "/".join(suffix))
    if settings.get(prefix + ("NativeProfile", "Servers")) not in {"ikev2-riga.tolf.is", "ikev2.tolf.is"}:
        raise ValueError("Unexpected VPN server")
    eap = settings.get(prefix + ("NativeProfile", "Authentication", "EAP", "Configuration"))
    if not eap:
        raise ValueError("Missing runtime EAP configuration")
    config = ET.fromstring(eap)
    ns = {"common": "http://www.microsoft.com/provisioning/EapCommon",
          "chap": "http://www.microsoft.com/provisioning/MsChapV2ConnectionPropertiesV1"}
    if config.findtext(".//common:Type", namespaces=ns) != "26":
        raise ValueError("Expected EAP-MSCHAPv2")
    if config.findtext(".//chap:UseWinLogonCredentials", namespaces=ns) != "false":
        raise ValueError("Windows login credentials must not be used")
    print("PASS: native runtime IKEv2, EAP, AES256/SHA256/Group14, routing; no EXE or scripts")
    for key, value in CRYPTO.items():
        print(key + "=" + value)

if __name__ == "__main__":
    verify(Path(sys.argv[1]))
