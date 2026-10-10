#!/usr/bin/env python3
"""Build isolated Cisco Start/Stop probes from the owner's native export."""
import argparse, copy, json, plistlib
from pathlib import Path
from urllib.request import Request, urlopen

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--sign", action="store_true")
    args = p.parse_args()
    source = plistlib.loads(args.source.read_bytes())
    actions = source["WFWorkflowActions"]
    expected = ["com.cisco.anyconnect.StartVpnIntent", "com.cisco.anyconnect.StopVpnIntent"]
    if [a["WFWorkflowActionIdentifier"] for a in actions] != expected:
        raise ValueError("Expected native Cisco Start/Stop export")
    if any(set(a["WFWorkflowActionParameters"]) - {"UUID"} for a in actions):
        raise ValueError("Unexpected parameters: review source before publishing")
    args.output.mkdir(parents=True, exist_ok=True)
    for i, suffix in enumerate(("ON", "OFF")):
        name = "TOLF-CISCO-" + suffix
        workflow = copy.deepcopy(source)
        action = copy.deepcopy(actions[i])
        action["WFWorkflowActionParameters"].pop("UUID", None)
        workflow["WFWorkflowActions"] = [action]
        workflow["WFWorkflowName"] = name
        workflow["WFWorkflowImportQuestions"] = []
        workflow["WFWorkflowIcon"]["WFWorkflowIconStartColor"] = 431817727 if i == 0 else 4282601983
        raw = plistlib.dumps(workflow, fmt=plistlib.FMT_XML, sort_keys=False)
        (args.output / (name + ".plist")).write_bytes(raw)
        if args.sign:
            body = json.dumps({"shortcutName":name, "shortcut":raw.decode()}).encode()
            req = Request("https://hubsign.routinehub.services/sign", data=body,
                headers={"Content-Type":"application/json", "User-Agent":"cherri/2.3.0"}, method="POST")
            with urlopen(req, timeout=40) as response:
                signed = response.read()
                if response.status != 200 or not signed.startswith(b"AEA1") or len(signed) < 2000:
                    raise ValueError("Invalid signing response")
            (args.output / (name + ".shortcut")).write_bytes(signed)
            print(name, len(signed), "bytes")
if __name__ == "__main__":
    main()
