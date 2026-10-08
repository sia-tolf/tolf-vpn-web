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
