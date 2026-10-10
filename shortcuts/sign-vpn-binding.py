#!/usr/bin/env python3
"""Fix Cherri VPNPicker encoding and sign a one-action iOS 26 pilot.

Requires Cherri to produce a debug .plist and skips signing the unpatched
binary. The external signing service receives NO credentials or certificates.
"""
import json
import plistlib
from pathlib import Path
from urllib.request import Request, urlopen

root = Path(__file__).resolve().parent
name = "TOLF VPN Binding Test"
source = root / (name + ".plist")
data = plistlib.loads(source.read_bytes())
actions = data.get("WFWorkflowActions", [])
assert len(actions) == 1, "Test must contain only one action"
action = actions[0]
assert action["WFWorkflowActionIdentifier"] == "is.workflow.actions.vpn.set"
params = action["WFWorkflowActionParameters"]
assert params["WFVPNOperation"] == "Set On Demand"
assert params["WFOnDemandValue"] is True
assert not data.get("WFWorkflowImportQuestions"), "No import questions allowed"
expected = {
    "identifier": "00000000-0000-0000-0000-000000000000",
    "title": "TOLF Москва iPhone",
}
# Cherri encodes a source dictionary as WFDictionaryFieldValue. Apple requires
# WFVPNConfiguration.wfSerializedRepresentation directly (identifier + title).
assert params.get("WFVPN", {}).get("WFSerializationType") == "WFDictionaryFieldValue"
params["WFVPN"] = expected

xml = plistlib.dumps(data, fmt=plistlib.FMT_XML, sort_keys=False)
assert plistlib.loads(xml)["WFWorkflowActions"][0]["WFWorkflowActionParameters"]["WFVPN"] == expected
print("PRODUCTION_VPN_CONFIG_SERIALIZATION_OK")
print("ACTION_COUNT=1, ON_DEMAND=ON, RUN_NOT_AUTOMATIC")

request = Request(
    "https://hubsign.routinehub.services/sign",
    data=json.dumps({"shortcutName": name, "shortcut": xml.decode("utf-8")}).encode("utf-8"),
    headers={"Content-Type": "application/json", "User-Agent": "cherri/2.3.0"},
    method="POST",
)
with urlopen(request, timeout=35) as response:
    assert response.status == 200, "HubSign HTTP non-200"
    assert response.headers.get_content_type() in {
        "application/octet-stream", "application/x-plist", "application/x-apple-shortcut"
    }, "HubSign response has unexpected MIME type"
    signed = response.read()
assert signed[:4] == b"AEA1" and len(signed) > 2000, "Not an Apple-signed Shortcut"
out = root / "probe" / "TOLF-VPN-Binding-Test.shortcut"
out.parent.mkdir(exist_ok=True)
out.write_bytes(signed)
print("SIGNED_VPN_BINDING_TEST_OK", len(signed), "bytes")
