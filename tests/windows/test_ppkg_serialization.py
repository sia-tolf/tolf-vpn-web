from xml.etree import ElementTree as ET
from ppkg.personalize import write_xml

def test_preserve_wcd_namespaces_and_xml_declaration(tmp_path):
    original = b'\xef\xbb\xbf<?xml version="1.0" encoding="utf-8" standalone="yes"?>\r\n<WindowsCustomizations><PackageConfig xmlns="urn:package"><ID>old</ID></PackageConfig><Settings xmlns="urn:settings"><VPN VPNProfileName="old"><Password>old</Password></VPN></Settings></WindowsCustomizations>'
    path = tmp_path/'customizations.xml'
    path.write_bytes(original)
    tree = ET.parse(path)
    tree.find('.//{urn:package}ID').text = '{new}'
    tree.find('.//{urn:settings}VPN').set('VPNProfileName', 'Test & "quoted"')
    tree.find('.//{urn:settings}Password').text = 'secret<&'
    write_xml(path, tree)
    result = path.read_bytes()
    assert result.startswith(original[:original.index(b'?>')+2])
    assert b'xmlns="urn:package"' in result
    assert b'xmlns="urn:settings"' in result
    assert b'ns0:' not in result
    restored = ET.parse(path)
    assert restored.find('.//{urn:settings}VPN').get('VPNProfileName') == 'Test & "quoted"'
    assert restored.find('.//{urn:settings}Password').text == 'secret<&'

def test_preserve_unqualified_runtime_scope(tmp_path):
    path = tmp_path/'certificate.provxml'
    path.write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\r\n<wap-provisioningdoc><characteristic scope="Device"><parm name="PFXCertBlob" value="old" /></characteristic></wap-provisioningdoc>')
    tree = ET.parse(path)
    tree.find('.//parm').set('value', 'new')
    write_xml(path, tree)
    root = ET.parse(path).getroot()
    assert root.tag == 'wap-provisioningdoc'
    assert root.find('characteristic').get('scope') == 'Device'
    assert root.find('.//parm').get('value') == 'new'

import pytest
from ppkg.personalize import preserve_local_routes

def routing_xml():
    return b'\xef\xbb\xbf<?xml version="1.0" encoding="utf-8" standalone="yes"?>\r\n<wap-provisioningdoc><characteristic type="VPNv2"><characteristic type="Test"><characteristic type="NativeProfile"><characteristic type="Authentication"><parm name="MachineMethod" value="Certificate" datatype="string" /></characteristic></characteristic><characteristic type="NativeProfile"><parm name="RoutingPolicyType" value="ForceTunnel" datatype="string" /><parm name="Servers" value="ikev2-riga.tolf.is" datatype="string" /></characteristic></characteristic></characteristic></wap-provisioningdoc>'

def test_preserve_local_routes_without_static_private_networks(tmp_path):
    path = tmp_path/'vpn.provxml'; path.write_bytes(routing_xml())
    before = ET.parse(path)
    preserve_local_routes(path)
    after = ET.parse(path)
    settings = after.findall(".//characteristic[@type='NativeProfile']/parm[@name='DisableClassBasedDefaultRoute']")
    assert len(settings) == 1
    assert settings[0].attrib == {'name':'DisableClassBasedDefaultRoute','value':'true','datatype':'boolean'}
    # Everything other than the class-route setting must be unchanged.
    next(node for node in after.iter('characteristic') if settings[0] in list(node)).remove(settings[0])
    assert ET.tostring(before.getroot()) == ET.tostring(after.getroot())
    assert path.read_bytes().startswith(routing_xml()[:routing_xml().index(b'?>')+2])

def test_local_route_setting_is_idempotent(tmp_path):
    path = tmp_path/'vpn.provxml'; path.write_bytes(routing_xml())
    preserve_local_routes(path); preserve_local_routes(path)
    assert len(ET.parse(path).findall(".//parm[@name='DisableClassBasedDefaultRoute']")) == 1

def test_local_route_setting_rejects_unexpected_policy(tmp_path):
    path = tmp_path/'vpn.provxml'; path.write_bytes(routing_xml().replace(b'ForceTunnel',b'SplitTunnel'))
    before=path.read_bytes()
    with pytest.raises(ValueError,match='routing policy'): preserve_local_routes(path)
    assert path.read_bytes() == before

from ppkg.personalize import use_profile_xml, CRYPTO

def complete_routing_xml():
    root = ET.fromstring(routing_xml())
    profile = root.find('characteristic/characteristic')
    for name, value in {'AlwaysOn':'false','RememberCredentials':'true'}.items():
        ET.SubElement(profile,'parm',name=name,value=value,datatype='boolean')
    native = profile.find("characteristic[@type='NativeProfile']")
    ET.SubElement(native,'parm',name='NativeProtocolType',value='Ikev2',datatype='string')
    # The compiler emitted crypto settings in two separate characteristics.
    crypto = ET.SubElement(native,'characteristic',type='CryptographySuite')
    for name, value in CRYPTO.items():
        parent = ET.SubElement(native,'characteristic',type='CryptographySuite') if name == 'PfsGroup' else crypto
        ET.SubElement(parent,'parm',name=name,value=value,datatype='string')
    return b'\xef\xbb\xbf<?xml version="1.0" encoding="utf-8" standalone="yes"?>\r\n'+ET.tostring(root)

def test_profile_xml_eliminates_duplicate_csp_nodes_and_preserves_settings(tmp_path):
    path=tmp_path/'vpn.provxml'; path.write_bytes(complete_routing_xml())
    preserve_local_routes(path)
    use_profile_xml(path)
    outer=ET.parse(path)
    profile=outer.find('characteristic/characteristic')
    assert len(list(profile)) == 1
    assert profile[0].get('name') == 'ProfileXML'
    assert not profile.findall('.//characteristic')
    inner=ET.fromstring(profile[0].get('value'))
    assert inner.tag == 'VPNProfile'
    assert len(inner.findall('NativeProfile')) == 1
    native=inner.find('NativeProfile')
    assert len(native.findall('CryptographySuite')) == 1
    assert native.findtext('Authentication/MachineMethod') == 'Certificate'
    assert native.findtext('Servers') == 'ikev2-riga.tolf.is'
    assert native.findtext('RoutingPolicyType') == 'SplitTunnel'
    assert [(r.findtext('Address'), r.findtext('PrefixSize'), r.findtext('Metric')) for r in inner.findall('Route')] == [('0.0.0.0','1','1'),('128.0.0.0','1','1')]
    assert native.findtext('NativeProtocolType') == 'IKEv2'
    assert native.findtext('DisableClassBasedDefaultRoute') == 'true'
    assert [e.tag for e in native] == ['Servers','RoutingPolicyType','NativeProtocolType','DisableClassBasedDefaultRoute','CryptographySuite','Authentication']
    assert [e.tag for e in native.find('CryptographySuite')] == ['AuthenticationTransformConstants','CipherTransformConstants','DHGroup','IntegrityCheckMethod','EncryptionMethod']
    assert native.find('CryptographySuite/PfsGroup') is None
    assert {e.tag:e.text for e in native.find('CryptographySuite')} == {k:v for k,v in CRYPTO.items() if k != 'PfsGroup'}
    assert b'&lt;VPNProfile&gt;' in path.read_bytes()
    assert path.read_bytes().startswith(b'\xef\xbb\xbf<?xml version="1.0" encoding="utf-8" standalone="yes"?>')

def test_profile_xml_rejects_conflicting_duplicate_settings(tmp_path):
    path=tmp_path/'vpn.provxml'; path.write_bytes(complete_routing_xml())
    preserve_local_routes(path)
    tree=ET.parse(path); native=tree.find('.//characteristic[@type="NativeProfile"]')
    ET.SubElement(native,'parm',name='Servers',value='unapproved.example',datatype='string')
    tree.write(path,encoding='utf-8',xml_declaration=True)
    with pytest.raises(ValueError,match='Conflicting'): use_profile_xml(path)
