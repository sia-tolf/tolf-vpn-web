"""WCD test customization. No credentials or production device identities."""
import argparse
from pathlib import Path
from xml.etree import ElementTree as ET
from profile import profile_xml, text

def customization(certificate=None, root_certificate=None, password=None):
    root = ET.Element("WindowsCustomizations")
    package = ET.SubElement(root, "PackageConfig", {"xmlns": "urn:schemas-Microsoft-com:Windows-ICD-Package-Config.v1.0"})
    for key, value in [
        ("ID", "{7b6e4279-f08e-4e80-b70c-1ea2d07d1083}"),
        ("Name", "TOLF PPKG native crypto test"), ("Version", "1.1"),
        ("OwnerType", "ITAdmin"), ("Rank", "0"),
    ]:
        text(package, key, value)
    common = ET.SubElement(ET.SubElement(ET.SubElement(root, "Settings", {"xmlns": "urn:schemas-microsoft-com:windows-provisioning"}), "Customizations"), "Common")
    profiles = ET.SubElement(common, "ConnectivityProfiles")
    vpn = ET.SubElement(profiles, "VPN")
    collection = ET.SubElement(vpn, "VPNSetting")
    config = ET.SubElement(collection, "VPNConfig", {"VPNProfileName": "TOLF PPKG Test"})
    settings = ET.SubElement(config, "VPNSettings")
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
    for setting in source.find("NativeProfile/CryptographySuite"):
        text(settings, setting.tag, setting.text)
    if certificate:
        for node in list(settings):
            if node.tag in {"AuthenticationUserMethod", "EAPConfiguration"}:
                settings.remove(node)
        text(settings, "AuthenticationMachineMethod", "Certificate")
        certificates = ET.SubElement(common, "Certificates")
        clients = ET.SubElement(certificates, "ClientCertificates")
        client = ET.SubElement(clients, "ClientCertificate", {"CertificateName": "TOLF Windows Test"})
        for key, value in [("CertificatePath", str(certificate)), ("CertificatePassword", password), ("ExportCertificate", "false"), ("KeyLocation", "3")]:
            text(client, key, value)
        roots = ET.SubElement(certificates, "RootCertificates")
        ca = ET.SubElement(roots, "RootCertificate", {"CertificateName": "TOLF Windows Test CA"})
        text(ca, "CertificatePath", str(root_certificate))
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--certificate", type=Path)
    parser.add_argument("--root-certificate", type=Path)
    parser.add_argument("--password")
    args = parser.parse_args()
    args.output.write_bytes(customization(args.certificate, args.root_certificate, args.password))

