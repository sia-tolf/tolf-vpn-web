"""Prototype native VPNv2 payload for a Windows-built PPKG.

This produces ProfileXML, NOT a compiled .ppkg. Package compilation and
user-scope deployment must be verified on Windows before enabling delivery.
"""
import argparse
from pathlib import Path
import uuid
from xml.etree import ElementTree as ET

HOSTS = {"riga": "ikev2-riga.tolf.is", "moscow": "ikev2.tolf.is"}
EAP_HOST = "http://www.microsoft.com/provisioning/EapHostConfig"
EAP_COMMON = "http://www.microsoft.com/provisioning/EapCommon"
EAP_BASE = "http://www.microsoft.com/provisioning/BaseEapConnectionPropertiesV1"
EAP_MSCHAP = "http://www.microsoft.com/provisioning/MsChapV2ConnectionPropertiesV1"

def text(parent, tag, value):
    child = ET.SubElement(parent, tag)
    child.text = value
    return child

def profile_xml(server, device_id, name):
    if server not in HOSTS:
        raise ValueError("Unsupported VPN server")
    identity = str(uuid.UUID(device_id))
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 64 or any(ord(c)<32 for c in name):
        raise ValueError("Invalid device name")
    profile = ET.Element("VPNProfile")
    text(profile, "ProfileName", "TOLF " + name.strip() + " " + identity)
    text(profile, "RememberCredentials", "true")
    text(profile, "AlwaysOn", "false")
    native = ET.SubElement(profile, "NativeProfile")
    text(native, "Servers", HOSTS[server])
    text(native, "RoutingPolicyType", "ForceTunnel")
    text(native, "NativeProtocolType", "Ikev2")
    crypto = ET.SubElement(native, "CryptographySuite")
    for key, value in [
        ("AuthenticationTransformConstants", "SHA256128"),
        ("CipherTransformConstants", "AES256"), ("PfsGroup", "None"),
        ("DHGroup", "Group14"), ("IntegrityCheckMethod", "SHA256"),
        ("EncryptionMethod", "AES256"),
    ]:
        text(crypto, key, value)
    auth = ET.SubElement(native, "Authentication")
    text(auth, "UserMethod", "Eap")
    configuration = ET.SubElement(ET.SubElement(auth, "Eap"), "Configuration")
    host = ET.SubElement(configuration, "{" + EAP_HOST + "}EapHostConfig")
    method = ET.SubElement(host, "{" + EAP_HOST + "}EapMethod")
    for key, value in [("Type","26"),("VendorId","0"),("VendorType","0"),("AuthorId","0")]:
        text(method, "{" + EAP_COMMON + "}" + key, value)
    config = ET.SubElement(host, "{" + EAP_HOST + "}Config")
    eap = ET.SubElement(config, "{" + EAP_BASE + "}Eap")
    text(eap, "{" + EAP_BASE + "}Type", "26")
    eap_type = ET.SubElement(eap, "{" + EAP_MSCHAP + "}EapType")
    text(eap_type, "{" + EAP_MSCHAP + "}UseWinLogonCredentials", "false")
    return ET.tostring(profile, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", choices=HOSTS, required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.suffix.lower() != ".xml":
        parser.error("Output is a source .xml file, not a compiled .ppkg")
    args.output.write_bytes(profile_xml(args.server, args.device_id, args.name))
