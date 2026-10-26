"""Render a DRAFT manifest using identity copied from Partner Center.
Does not compile, install, sign or submit a package.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = 'http://schemas.microsoft.com/appx/manifest/foundation/windows10'
ET.register_namespace('', NS)
ET.register_namespace('uap', 'http://schemas.microsoft.com/appx/manifest/uap/windows10')
ET.register_namespace('rescap', 'http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities')

def render(identity):
    fields = ('identityName', 'publisher', 'publisherDisplayName')
    if any(not isinstance(identity.get(k), str) or not identity[k].strip() or
           identity[k].startswith('COPY ') or '__' in identity[k] for k in fields):
        raise ValueError('Copy all three exact identity values from Partner Center')
    if not re.fullmatch(r'[A-Za-z0-9.-]{3,50}', identity['identityName']):
        raise ValueError('Invalid Package/Identity/Name')
    if not identity['publisher'].startswith('CN='):
        raise ValueError('Publisher must be the exact distinguished name from Partner Center')
    tree = ET.parse(Path(__file__).with_name('AppxManifest.template.xml'))
    root = tree.getroot()
    root.find(f'{{{NS}}}Identity').set('Name', identity['identityName'])
    root.find(f'{{{NS}}}Identity').set('Publisher', identity['publisher'])
    root.find(f'{{{NS}}}Properties/{{{NS}}}PublisherDisplayName').text = identity['publisherDisplayName']
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: render-manifest.py identity.json OUTPUT/AppxManifest.xml')
    data = render(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
    output = Path(sys.argv[2]); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    print('Draft manifest rendered; native package adaptation and certification checks are still required.')
