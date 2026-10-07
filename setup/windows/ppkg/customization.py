"""WCD test customization. No credentials or production device identities."""
import argparse
from pathlib import Path
from xml.etree import ElementTree as ET
from profile import profile_xml, text

def customization():
    root = ET.Element("WindowsCustomizations")
    package = ET.SubElement(root, "PackageConfig")
    for key, value in [
        ("ID", "{7b6e4279-f08e-4e80-b70c-1ea2d07d1083}"),
        ("Name", "TOLF PPKG compiler test"), ("Version", "1.0"),
        ("OwnerType", "ITAdmin"), ("Rank", "0"),
    ]:
        text(package, key, value)
    common = ET.SubElement(ET.SubElement(ET.SubElement(root, "Settings"), "Customizations"), "Common")
    profiles = ET.SubElement(common, "ConnectivityProfiles")
    vpn = ET.SubElement(profiles, "VPN")
    settings = ET.SubElement(vpn, "VPNSetting", {"Name": "TOLF PPKG Test"})
    source = ET.fromstring(profile_xml("riga", "7b6e4279-f08e-4e80-b70c-1ea2d07d1083", "Compiler test"))
    eap = source.find("NativeProfile/Authentication/Eap/Configuration")[0]
    for key, value in [
        ("ProfileType", "Native"), ("AlwaysOn", "false"),
        ("RememberCredentials", "true"), ("AuthenticationUserMethod", "EAP"),
        ("EAPConfiguration", ET.tostring(eap, encoding="unicode")),
        ("NativeProtocolType", "IKEv2"), ("RoutingPolicyType", "ForceTunnel"),
        ("Server", "ikev2-riga.tolf.is"),
    ]:
        text(settings, key, value)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_bytes(customization())
