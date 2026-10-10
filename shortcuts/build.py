#!/usr/bin/env python3
"""Build device-specific VPN commands from a native, working Apple export."""
import argparse
import copy
import plistlib
from pathlib import Path

def make_shortcut(source, on):
    data = copy.deepcopy(source)
    actions = data.get("WFWorkflowActions", [])
    if len(actions) != 2 or any(a.get("WFWorkflowActionIdentifier") != "is.workflow.actions.vpn.set" for a in actions):
        raise ValueError("Expected two native Set VPN actions")
    first, second = [a["WFWorkflowActionParameters"] for a in actions]
    if first.get("WFVPNOperation") != "Set On Demand" or second.get("WFVPNOperation", "Connect") != "Connect":
        raise ValueError("Source must enable On Demand, then Connect")
    vpn = first.get("WFVPN")
    if not isinstance(vpn, dict) or not vpn.get("identifier") or not vpn.get("appDescriptor") or vpn != second.get("WFVPN"):
        raise ValueError("Both actions must contain the same native VPN configuration")
    if first.get("WFOnDemandValue", True) is not True:
        raise ValueError("Source must be the working ON command")
    if data.get("WFWorkflowImportQuestions"):
        raise ValueError("Source must have no import questions")
    # Preserve Apple's exported defaults for ON. OFF changes only two parameters.
    if not on:
        first["WFOnDemandValue"] = False
        second["WFVPNOperation"] = "Disconnect"
    return data

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Unsigned plist from a working native ON export")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "unsigned")
    args = parser.parse_args()
    source = plistlib.loads(args.source.read_bytes())
    args.output.mkdir(parents=True, exist_ok=True)
    for on, name in [(True, "TOLF ON"), (False, "TOLF OFF")]:
        data = make_shortcut(source, on)
        path = args.output / (name + ".shortcut")
        path.write_bytes(plistlib.dumps(data, fmt=plistlib.FMT_BINARY, sort_keys=False))
        print(name, "validated, unsigned", path.stat().st_size)
if __name__ == "__main__":
    main()
