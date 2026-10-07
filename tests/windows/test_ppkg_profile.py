import importlib.util
from pathlib import Path
from xml.etree import ElementTree as ET
import uuid
import pytest
source = Path(__file__).resolve().parents[2]/"setup/windows/ppkg/profile.py"
spec = importlib.util.spec_from_file_location("ppkg_profile", source)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

def test_native_payload_is_separate_and_escapes_device_name():
    a, b = str(uuid.uuid4()), str(uuid.uuid4())
    root = ET.fromstring(p.profile_xml("moscow", a, "Office <PC> & Riga"))
    other = ET.fromstring(p.profile_xml("riga", b, "Office <PC> & Riga"))
    assert root.findtext("ProfileName") != other.findtext("ProfileName")
    assert "Office <PC> & Riga" in root.findtext("ProfileName")
    assert root.findtext("NativeProfile/Servers") == "ikev2.tolf.is"
    assert root.findtext("NativeProfile/CryptographySuite/DHGroup") == "Group14"
    assert root.findtext("NativeProfile/Authentication/UserMethod") == "Eap"
    assert root.findtext("AlwaysOn") == "false"
    assert not root.findall(".//Password")
    assert not root.findall(".//Command")

@pytest.mark.parametrize("server,identity,name", [
 ("https://attacker.example/",str(uuid.uuid4()),"PC"),
 ("riga","not-a-uuid","PC"), ("riga",str(uuid.uuid4()),""),
 ("riga",str(uuid.uuid4()),"PC" + chr(10)),
])
def test_rejects_invalid_input(server,identity,name):
    with pytest.raises(ValueError):
        p.profile_xml(server, identity, name)
