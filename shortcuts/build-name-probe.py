#!/usr/bin/env python3
"""Experimental name-to-VPN conversion; iPhone execution is the release gate."""
import argparse
import copy
import importlib.util
import json
import plistlib
from pathlib import Path
import urllib.request
import uuid

spec = importlib.util.spec_from_file_location("native_builder", Path(__file__).with_name("build.py"))
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)

def make_probe(source, vpn_name):
    if not vpn_name or not isinstance(vpn_name, str):
        raise ValueError("A non-empty VPN name is required")
    workflow = native.make_shortcut(source, True)
    text_id = str(uuid.uuid4()).upper()
    variable = {"Value": {"Type":"ActionOutput", "OutputUUID":text_id, "OutputName":"Text"},
                "WFSerializationType":"WFTextTokenAttachment"}
    for action in workflow["WFWorkflowActions"]:
        params = action["WFWorkflowActionParameters"]
        params["WFVPN"] = copy.deepcopy(variable)
        params.pop("UUID", None)
    workflow["WFWorkflowActions"].insert(0, {
        "WFWorkflowActionIdentifier":"is.workflow.actions.gettext",
        "WFWorkflowActionParameters":{"WFTextActionText":vpn_name, "UUID":text_id}})
    workflow["WFWorkflowName"] = "TOLF NAME TEST"
    workflow["WFWorkflowImportQuestions"] = []
    workflow["WFWorkflowIcon"]["WFWorkflowIconStartColor"] = 463140863
    return workflow

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--vpn-name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sign", action="store_true")
    args = parser.parse_args()
    source = plistlib.loads(args.source.read_bytes())
    workflow = make_probe(source, args.vpn_name)
    data = plistlib.dumps(workflow, fmt=plistlib.FMT_XML, sort_keys=False)
    assert source["WFWorkflowActions"][0]["WFWorkflowActionParameters"]["WFVPN"]["identifier"].encode() not in data
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "TOLF-NAME-TEST.plist").write_bytes(data)
    if args.sign:
        request = urllib.request.Request("https://hubsign.routinehub.services/sign",
            data=json.dumps({"shortcutName":workflow["WFWorkflowName"],"shortcut":data.decode()}).encode(),
            headers={"Content-Type":"application/json","User-Agent":"cherri/2.3.0"}, method="POST")
        with urllib.request.urlopen(request, timeout=40) as response:
            signed = response.read()
        if not signed.startswith(b"AEA1") or len(signed) < 2000:
            raise RuntimeError("Invalid shortcut signature response")
        (args.output / "TOLF-NAME-TEST.shortcut").write_bytes(signed)
    print("Built name-binding experiment; not verified on iPhone")

if __name__ == "__main__":
    main()
