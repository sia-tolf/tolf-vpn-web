from xml.etree import ElementTree as ET
import importlib.util
from pathlib import Path
from test_ppkg_serialization import complete_routing_xml
from ppkg.personalize import preserve_local_routes, CRYPTO
import sys

def test_candidate_merges_native_csp_nodes_without_changing_values(tmp_path):
    source = Path(__file__).resolve().parents[2] / 'setup/windows/ppkg/native_candidate.py'
    spec = importlib.util.spec_from_file_location('native_candidate', source)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(source.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    path = tmp_path/'vpn.provxml'
    path.write_bytes(complete_routing_xml())
    preserve_local_routes(path)
    module.use_native_nodes(path)
    root = ET.parse(path)
    native = root.findall(".//characteristic[@type='NativeProfile']")
    assert len(native) == 1
    crypto = native[0].findall("characteristic[@type='CryptographySuite']")
    assert len(crypto) == 1
    assert {p.get('name'):p.get('value') for p in crypto[0]} == {k:v for k,v in CRYPTO.items() if k != 'PfsGroup'}
    assert native[0].find("characteristic[@type='Authentication']/parm").attrib == {'name':'MachineMethod','value':'Certificate','datatype':'string'}
    assert native[0].find("parm[@name='DisableClassBasedDefaultRoute']").get('value') == 'true'
    assert not root.findall(".//parm[@name='ProfileXML']")
    assert path.read_bytes().startswith(b'\xef\xbb\xbf<?xml')
