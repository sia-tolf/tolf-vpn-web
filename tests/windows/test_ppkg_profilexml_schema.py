from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from lxml import etree

from ppkg.personalize import preserve_local_routes, use_profile_xml
from test_ppkg_serialization import complete_routing_xml

SCHEMA = etree.XMLSchema(etree.parse(str(
    Path(__file__).parent / "fixtures/vpnv2-machine-profilexml.xsd"
)))


def generated_profile(tmp_path):
    path = tmp_path / "vpn.provxml"
    path.write_bytes(complete_routing_xml())
    preserve_local_routes(path)
    use_profile_xml(path)
    value = ET.parse(path).find(".//parm").get("value")
    return etree.fromstring(value.encode())


def test_generated_machine_profile_conforms_to_published_xsd(tmp_path):
    SCHEMA.assertValid(generated_profile(tmp_path))


@pytest.mark.parametrize("parent, child", [
    (".", "RememberCredentials"),
    ("NativeProfile", "Servers"),
    ("NativeProfile/CryptographySuite", "PfsGroup"),
])
def test_schema_rejects_out_of_sequence_payload(tmp_path, parent, child):
    profile = generated_profile(tmp_path)
    target = profile if parent == "." else profile.find(parent)
    element = target.find(child)
    target.remove(element)
    target.append(element)
    with pytest.raises(etree.DocumentInvalid):
        SCHEMA.assertValid(profile)
