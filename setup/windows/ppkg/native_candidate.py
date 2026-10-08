"""Diagnostic PPKG candidate: consolidate native CSP nodes without ProfileXML.

Imported by build.py only. Production personalization remains unchanged until
a real Windows crypto readback confirms all six values.
"""
from xml.dom import minidom, Node
from xml.etree import ElementTree as ET
import personalize

_profile_xml = personalize.use_profile_xml

def use_native_nodes(path):
    # Reuse strict template validation and value escaping.
    _profile_xml(path)
    original = path.read_bytes()
    outer = ET.fromstring(original)
    value = outer.find('.//parm').get('value')
    vpn = ET.fromstring(value)
    document = minidom.parseString(original)
    provider = next(n for n in document.getElementsByTagName('characteristic')
                    if n.getAttribute('type') == 'VPNv2')
    target = next(n for n in provider.childNodes if n.nodeType == Node.ELEMENT_NODE)
    for child in list(target.childNodes):
        target.removeChild(child)
    def append(parent, element):
        if len(element):
            node = document.createElement('characteristic')
            node.setAttribute('type', element.tag)
            parent.appendChild(node)
            for child in element:
                append(node, child)
        else:
            node = document.createElement('parm')
            node.setAttribute('name', element.tag)
            node.setAttribute('value', element.text)
            node.setAttribute('datatype', 'boolean' if element.text in ('true', 'false') else 'string')
            parent.appendChild(node)
    for element in vpn:
        append(target, element)
    prefix = original[:original.index(b'?>') + 2]
    result = prefix + b'\r\n' + document.documentElement.toxml(encoding='utf-8') + b'\r\n'
    root = ET.fromstring(result)
    native = root.findall(".//characteristic[@type='NativeProfile']")
    if len(native) != 1 or len(native[0].findall("characteristic[@type='CryptographySuite']")) != 1:
        raise ValueError('Duplicate native CSP node')
    restored = {p.get('name'):p.get('value') for p in root.iter('parm')}
    expected = {e.tag:e.text for e in vpn.iter() if not len(e)}
    if restored != expected or 'ProfileXML' in restored:
        raise ValueError('Native CSP settings changed')
    path.write_bytes(result)

def activate():
    personalize.use_profile_xml = use_native_nodes
