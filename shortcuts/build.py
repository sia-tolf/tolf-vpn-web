#!/usr/bin/env python3
"""Create unsigned TOLF ON/OFF shortcuts for Apple signing on a Mac.

Unsigned files are not installable on iPhone. A signed build is required.
"""
import plistlib
import uuid
from pathlib import Path

DIR = Path(__file__).resolve().parent
OUT = DIR / "unsigned"
OUT.mkdir(exist_ok=True)
VPN_ACTION = "is.workflow.actions.vpn.set"
VERSIONS = {
    "WFWorkflowClientVersion": "3612.0.1.1",
    "WFWorkflowMinimumClientVersion": 900,
    "WFWorkflowMinimumClientVersionString": "900",
    "WFWorkflowIsDisabledOnLockScreen": True,
    "WFWorkflowHasOutputFallback": False,
    "WFWorkflowHasShortcutInputVariables": False,
    "WFWorkflowTypes": [],
    "WFQuickActionSurfaces": [],
    "WFWorkflowInputContentItemClasses": [],
    "WFWorkflowOutputContentItemClasses": [],
}

def make_shortcut(name, on):
    actions = []
    operations = ("Set On Demand", "Connect" if on else "Disconnect")
    for index, operation in enumerate(operations):
        unique = str(uuid.uuid5(uuid.NAMESPACE_URL, "https://tolf.is/shortcuts/"+name+"/"+str(index))).upper()
        params = {"UUID": unique, "WFVPNOperation": operation}
        if index == 0:
            params["WFOnDemandValue"] = 1 if on else 0
        actions.append({
            "WFWorkflowActionIdentifier": VPN_ACTION,
            "WFWorkflowActionParameters": params,
        })
    questions = [
        {
            "ActionIndex": index,
            "Category": "Parameter",
            "ParameterKey": "WFVPN",
            "Text": "Выберите соединение TOLF AnyConnect для шага "+str(index+1),
        }
        for index in range(2)
    ]
    return {
        **VERSIONS,
        "WFWorkflowName": name,
        "WFWorkflowIcon": {
            "WFWorkflowIconStartColor": 463140863 if on else 4282601983,
            "WFWorkflowIconGlyphNumber": 62068,
        },
        "WFWorkflowImportQuestions": questions,
        "WFWorkflowActions": actions,
    }

for name, on in (("TOLF ON", True), ("TOLF OFF", False)):
    path = OUT / (name + ".shortcut")
    path.write_bytes(plistlib.dumps(make_shortcut(name, on), fmt=plistlib.FMT_BINARY))
    print(path.name, path.stat().st_size, "bytes, unsigned")
