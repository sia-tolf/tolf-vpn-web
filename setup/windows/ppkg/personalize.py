"""Personalize a verified Microsoft-compiled certificate PPKG on UK.

Native provisioning payload only. No executable or script is placed in the WIM.
"""
import base64
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
from xml.dom import minidom, Node
from xml.etree import ElementTree as ET
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import pkcs12

TEMPLATE = Path('/opt/tolf-api/windows-ppkg-template')
TEMPLATE_PACKAGE = Path('/opt/tolf-api/windows-ppkg-template.ppkg')
WIMLIB = Path('/opt/tolf-api/wimtools/usr/bin/wimlib-imagex')
LIBRARIES = Path('/opt/tolf-api/wimtools/usr/lib/x86_64-linux-gnu')
HOSTS = {'riga': 'ikev2-riga.tolf.is', 'moscow': 'ikev2.tolf.is'}
CRYPTO = {'AuthenticationTransformConstants':'SHA256128', 'CipherTransformConstants':'AES256',
          'PfsGroup':'None', 'DHGroup':'Group14', 'IntegrityCheckMethod':'SHA256', 'EncryptionMethod':'AES256'}

def available():
    return TEMPLATE.is_dir() and TEMPLATE_PACKAGE.is_file() and WIMLIB.is_file()

def write_xml(path, tree):
    """Keep WCD namespace declarations, encoding, BOM and XML declaration.

    ElementTree is used to validate and edit values, but must not rewrite the
    compiler's document with generated ns0/ns1 prefixes.
    """
    original = path.read_bytes()
    document = minidom.parseString(original)
    elements = [document.documentElement, *document.documentElement.getElementsByTagName('*')]
    edited = list(tree.iter())
    if len(elements) != len(edited):
        raise ValueError('PPKG XML structure changed')
    for node, value in zip(elements, edited):
        tag = ('{' + node.namespaceURI + '}' if node.namespaceURI else '') + node.localName
        if tag != value.tag:
            raise ValueError('PPKG XML namespace changed')
        for name, attribute in value.attrib.items():
            node.setAttribute(name, attribute)
        texts = [child for child in node.childNodes if child.nodeType == Node.TEXT_NODE]
        if not node.getElementsByTagName('*') and value.text is not None:
            for child in texts: node.removeChild(child)
            node.appendChild(document.createTextNode(value.text))
    prefix = original[:original.index(b'?>') + 2]
    result = prefix + b'\r\n' + document.documentElement.toxml(encoding='utf-8') + b'\r\n'
    # Check that preserving the original namespace spelling changed no values.
    if ET.tostring(ET.fromstring(result)) != ET.tostring(tree.getroot()):
        # Whitespace-only tails are immaterial; compare the actual settings.
        def settings(root):
            return [(e.tag, e.attrib, (e.text or '').strip()) for e in root.iter()]
        if settings(ET.fromstring(result)) != settings(tree.getroot()):
            raise ValueError('PPKG XML serialization changed settings')
    path.write_bytes(result)

def run(args):
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = str(LIBRARIES)
    result = subprocess.run([str(WIMLIB), *args], capture_output=True, env=env, timeout=40)
    if result.returncode:
        raise RuntimeError('Native PPKG packaging failed')
    return result.stdout

def preserve_local_routes(path):
    """Avoid a class-wide VPN route without inventing physical gateways.

    ForceTunnel changes default routes; existing more-specific physical routes
    still win. Disabling the class route prevents an assigned 10.x VPN address
    from additionally capturing all of 10/8. A static PPKG cannot enumerate the
    destination computer's live routes or protect management over a default
    gateway without an existing specific route.
    """
    original = path.read_bytes()
    root = ET.fromstring(original)
    profile = root.find("characteristic[@type='VPNv2']/characteristic")
    if profile is None or root.tag != 'wap-provisioningdoc':
        raise ValueError('Expected native Windows VPN provisioning XML')
    policies = profile.findall("characteristic[@type='NativeProfile']/parm[@name='RoutingPolicyType']")
    if len(policies) != 1 or policies[0].get('value') != 'ForceTunnel':
        raise ValueError('Unexpected Windows routing policy')
    document = minidom.parseString(original)
    native = next(node for node in document.getElementsByTagName('characteristic')
                  if node.getAttribute('type') == 'NativeProfile')
    settings = [node for node in document.getElementsByTagName('parm')
                if node.getAttribute('name') == 'DisableClassBasedDefaultRoute']
    if len(settings) > 1:
        raise ValueError('Conflicting Windows class route settings')
    if settings:
        setting = settings[0]
        if setting.parentNode.getAttribute('type') != 'NativeProfile':
            raise ValueError('Wrong Windows class route setting scope')
    else:
        setting = document.createElement('parm')
        setting.setAttribute('name', 'DisableClassBasedDefaultRoute')
        native.appendChild(setting)
    setting.setAttribute('value', 'true')
    setting.setAttribute('datatype', 'boolean')
    prefix = original[:original.index(b'?>') + 2]
    result = prefix + b'\r\n' + document.documentElement.toxml(encoding='utf-8') + b'\r\n'
    ET.fromstring(result)
    path.write_bytes(result)

def use_profile_xml(path):
    """Configure VPNv2 in one ProfileXML value, not repeated CSP Add nodes."""
    original = path.read_bytes()
    root = ET.fromstring(original)
    profile = root.find("characteristic[@type='VPNv2']/characteristic")
    if profile is None:
        raise ValueError('Missing Windows VPN profile')
    settings = {}
    for parm in profile.iter('parm'):
        name, value = parm.get('name'), parm.get('value')
        if name in settings and settings[name] != value:
            raise ValueError('Conflicting native VPN settings')
        settings[name] = value
    expected = set(CRYPTO) | {'AlwaysOn', 'RememberCredentials', 'MachineMethod',
                            'NativeProtocolType', 'RoutingPolicyType', 'Servers',
                            'DisableClassBasedDefaultRoute'}
    if (set(settings) != expected or settings['MachineMethod'] != 'Certificate'
            or settings['RoutingPolicyType'] != 'ForceTunnel'
            or settings['DisableClassBasedDefaultRoute'] != 'true'
            or settings['AlwaysOn'] != 'false'
            or settings['NativeProtocolType'].upper() != 'IKEV2'
            or settings['Servers'] not in HOSTS.values()
            or any(settings[k] != v for k, v in CRYPTO.items())):
        raise ValueError('Unsafe Windows ProfileXML settings')
    # Windows 10 consumes CryptographySuite sequentially; putting PfsGroup
    # before EncryptionMethod/IntegrityCheckMethod/DHGroup leaves those unset.
    # Use the Windows 10 ProfileXML sequence, not the newer published XSD order.
    vpn = ET.Element('VPNProfile')
    for name in ('RememberCredentials', 'AlwaysOn'):
        ET.SubElement(vpn, name).text = settings[name]
    native = ET.SubElement(vpn, 'NativeProfile')
    for name in ('Servers', 'RoutingPolicyType', 'NativeProtocolType', 'DisableClassBasedDefaultRoute'):
        ET.SubElement(native, name).text = 'IKEv2' if name == 'NativeProtocolType' else settings[name]
    crypto = ET.SubElement(native, 'CryptographySuite')
    for name in ('AuthenticationTransformConstants', 'CipherTransformConstants',
                 'PfsGroup', 'DHGroup', 'IntegrityCheckMethod', 'EncryptionMethod'):
        ET.SubElement(crypto, name).text = settings[name]
    ET.SubElement(ET.SubElement(native, 'Authentication'), 'MachineMethod').text = 'Certificate'
    value = ET.tostring(vpn, encoding='unicode')
    document = minidom.parseString(original)
    provider = next(n for n in document.documentElement.childNodes
                    if n.nodeType == Node.ELEMENT_NODE and n.getAttribute('type') == 'VPNv2')
    target = next(n for n in provider.childNodes if n.nodeType == Node.ELEMENT_NODE)
    for child in list(target.childNodes):
        target.removeChild(child)
    parm = document.createElement('parm')
    parm.setAttribute('name', 'ProfileXML')
    parm.setAttribute('value', value)
    parm.setAttribute('datatype', 'string')
    target.appendChild(parm)
    prefix = original[:original.index(b'?>') + 2]
    result = prefix + b'\r\n' + document.documentElement.toxml(encoding='utf-8') + b'\r\n'
    restored = ET.fromstring(result).find('.//parm')
    if restored.get('name') != 'ProfileXML' or restored.get('value') != value:
        raise ValueError('Windows ProfileXML escaping failed')
    path.write_bytes(result)

def build(row, pfx, password, ca_der):
    identity = str(uuid.UUID(row['id']))
    if row['server'] not in HOSTS or not isinstance(row['name'], str) or not 1 <= len(row['name'].strip()) <= 64 or any(ord(c)<32 for c in row['name']):
        raise ValueError('Invalid Windows package identity')
    key, cert, chain = pkcs12.load_key_and_certificates(pfx, password.encode())
    ca = x509.load_der_x509_certificate(ca_der)
    expected = 'tolf-win-' + uuid.UUID(identity).hex + '.tolf.is'
    if key is None or cert is None or cert.subject.rfc4514_string() != 'CN=' + expected or ca.subject != cert.issuer:
        raise ValueError('Certificate does not belong to this Windows device')
    if key.public_key().public_numbers() != cert.public_key().public_numbers():
        raise ValueError('Certificate key mismatch')
    if not any(item.fingerprint(hashes.SHA256()) == ca.fingerprint(hashes.SHA256()) for item in chain or []):
        raise ValueError('Client PFX has the wrong CA')
    display = ''.join('-' if c in '<>:"/\\|?*%#' else c for c in row['name'].strip())
    profile = 'TOLF ' + display + ' ' + identity
    certificate_name = 'TOLF Windows ' + uuid.UUID(identity).hex
    ca_hash = hashlib.sha1(ca_der).hexdigest().upper()  # Windows certificate thumbprint, not a signature.
    with tempfile.TemporaryDirectory(prefix='tolf-ppkg-') as tmp:
        directory = Path(tmp) / 'payload'
        shutil.copytree(TEMPLATE, directory)
        for path in directory.rglob('*'):
            if path.is_file() and path.suffix.lower() not in {'.xml','.provxml'}:
                raise ValueError('Unexpected PPKG template file')
        runtimes = list(directory.rglob('*.provxml'))
        if len(runtimes) != 3: raise ValueError('Unexpected certificate PPKG template')
        providers = set()
        for path in runtimes:
            tree = ET.parse(path); root = tree.getroot()
            for provider in root.findall('characteristic'):
                kind = provider.get('type'); providers.add(kind)
                if kind == 'VPNv2':
                    provider.find('characteristic').set('type', profile)
                    settings = {p.get('name'):p.get('value') for p in provider.iter('parm')}
                    if settings.get('MachineMethod') != 'Certificate' or any(settings.get(k) != v for k,v in CRYPTO.items()) or 'UserMethod' in settings:
                        raise ValueError('Unsafe native VPN template')
                    for parm in provider.iter('parm'):
                        if parm.get('name') == 'Servers': parm.set('value', HOSTS[row['server']])
                elif kind == 'ClientCertificateInstall':
                    if provider.get('scope') != 'Device': raise ValueError('Wrong certificate store')
                    provider.find('characteristic/characteristic').set('type', certificate_name)
                    settings = {p.get('name'):p.get('value') for p in provider.iter('parm')}
                    if settings.get('KeyLocation') != '3' or settings.get('PFXKeyExportable') != 'false':
                        raise ValueError('Unsafe certificate key template')
                    for parm in provider.iter('parm'):
                        if parm.get('name') == 'PFXCertBlob': parm.set('value', base64.b64encode(pfx).decode())
                        if parm.get('name') == 'PFXCertPassword': parm.set('value', password)
                elif kind == 'RootCATrustedCertificates':
                    if provider.get('scope') != 'Device': raise ValueError('Wrong authority store')
                    provider.find('characteristic/characteristic').set('type', ca_hash)
                    for parm in provider.iter('parm'):
                        if parm.get('name') != 'EncodedCertificate': raise ValueError('Unexpected authority setting')
                        parm.set('value', base64.b64encode(ca_der).decode())
                else: raise ValueError('Unexpected provisioning provider')
            write_xml(path, tree)
            if root.find("characteristic[@type='VPNv2']") is not None:
                preserve_local_routes(path)
                use_profile_xml(path)
        if providers != {'VPNv2','ClientCertificateInstall','RootCATrustedCertificates'}:
            raise ValueError('Missing native certificate settings')
        # Preserve the compiler's runtime ordering and atomic groups; namespace each group to the device.
        runtime_index = directory/'Multivariant/0/Prov/RunTime.xml'
        tree = ET.parse(runtime_index)
        for element in tree.getroot():
            element.set('SettingsGroup', str(uuid.uuid5(uuid.UUID(identity), element.get('SettingsGroup'))))
        write_xml(runtime_index, tree)
        for path in directory.rglob('*.xml'):
            if path == runtime_index: continue
            tree = ET.parse(path)
            for element in tree.iter():
                local = element.tag.split('}')[-1]
                if local == 'ID': element.text = '{' + identity + '}'
                if local == 'Name' and element.text == 'TOLF PPKG native crypto test': element.text = profile
                if local == 'Version': element.text = '2.4'
                if local == 'Server': element.text = HOSTS[row['server']]
                if local == 'CertificatePassword': element.text = password
                if 'VPNProfileName' in element.attrib: element.set('VPNProfileName', profile)
                if 'CertificateName' in element.attrib:
                    element.set('CertificateName', certificate_name if local == 'ClientCertificate' else 'TOLF Windows IKEv2 Device CA')
            write_xml(path, tree)
        package = Path(tmp)/'TOLF.ppkg'
        # Update the genuine WCD container rather than constructing a new WIM.
        shutil.copyfile(TEMPLATE_PACKAGE, package)
        run(['update',str(package),'1','--no-acls','--command', 'add "'+str(directory)+'" /'])
        run(['info',str(package),'1','--image-property','NAME='+profile,'--image-property','PACKAGEID={'+identity+'}',
             '--image-property','VERSION=2.4','--image-property','ALTITUDE=5000',
             '--image-property','RESETCLEAR=0','--image-property','NOTES=VERSION=10.0.26100.9457;Source=CLI;;TargetSkus=Invalid;EncryptPackage=False;SignPackage=False;PackageID='+identity+';'])
        # Read the produced WIM back; verify the same exact payload was stored.
        extracted = Path(tmp)/'verify'
        run(['apply',str(package),'1',str(extracted),'--no-acls'])
        for path in directory.rglob('*'):
            if path.is_file() and (extracted/path.relative_to(directory)).read_bytes() != path.read_bytes():
                raise ValueError('PPKG payload round trip failed')
        result = package.read_bytes()
        if not result.startswith(b'MSWIM'): raise ValueError('Invalid PPKG container')
        return result



