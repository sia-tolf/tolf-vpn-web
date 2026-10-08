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
