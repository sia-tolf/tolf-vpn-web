"""Signed Cisco shortcuts using the owner's verified native intent parameters."""
import hashlib
import json
import os
import plistlib
import tempfile
import time
import threading
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

_LOCK = threading.Lock()
CACHE = Path("/var/lib/tolf-api/ios-shortcuts")
VERSION = "cisco-controller-v2"

def vpn_name(row, entry_name):
    return "TOLF " + entry_name + " " + str(row["label"])[:36]

def workflow(name, mode):
    if mode not in ("on", "off"):
        raise ValueError("Unsupported shortcut")
    if not isinstance(name, str) or not name or len(name) > 100:
        raise ValueError("Invalid VPN name")
    return {
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowClientVersion": "4711.2",
        "WFWorkflowName": "TOLF " + mode.upper(),
        "WFWorkflowIcon": {"WFWorkflowIconStartColor": 431817727 if mode == "on" else 4282601983,
                           "WFWorkflowIconGlyphNumber": 59760},
        "WFWorkflowActions": [
            {"WFWorkflowActionIdentifier": "com.cisco.anyconnect." + ("StartVpnIntent" if mode == "on" else "StopVpnIntent"),
             "WFWorkflowActionParameters": {"vpnConfig": name} if mode == "on" else {}},
            {"WFWorkflowActionIdentifier": "is.workflow.actions.returntohomescreen", "WFWorkflowActionParameters": {}}
        ],
        "WFWorkflowImportQuestions": [],
        "WFWorkflowTypes": ["WFWorkflowTypeShowInSearch"],
        "WFWorkflowInputContentItemClasses": [],
        "WFWorkflowOutputContentItemClasses": [],
        "WFWorkflowHasOutputFallback": False,
        "WFWorkflowHasShortcutInputVariables": False,
        "WFQuickActionSurfaces": []
    }

def controller(name):
    doc = workflow(name, "on")
    doc["WFWorkflowName"] = "TOLF"
    doc["WFWorkflowHasShortcutInputVariables"] = True
    doc["WFWorkflowInputContentItemClasses"] = ["WFStringContentItem"]
    text_id = "4B5FF2D1-1B38-4D57-AD77-2C1B195ED02A"
    # Materialize a Text action so If resolves a string operand during import.
    # Raw Shortcut Input has no concrete content type when the editor validates it.
    actions = [{"WFWorkflowActionIdentifier":"is.workflow.actions.gettext",
                "WFWorkflowActionParameters":{
                    "UUID":text_id,
                    "WFTextActionText":{
                        "Value":{"string":"\uFFFC", "attachmentsByRange":{
                            "{0, 1}":{"Type":"ExtensionInput"}}},
                        "WFSerializationType":"WFTextTokenString"}}}]

    for mode in ("on", "off"):
        group = str(uuid.uuid5(uuid.NAMESPACE_URL, "https://vpn.tolf.is/controller/" + mode)).upper()
        actions.extend([
            {"WFWorkflowActionIdentifier":"is.workflow.actions.conditional",
             "WFWorkflowActionParameters":{
                 "GroupingIdentifier":group, "WFControlFlowMode":0,
                 "WFInput":{"Type":"Variable", "Variable":{
                     "Value":{"Type":"ActionOutput", "OutputUUID":text_id, "OutputName":"Text",
                              "Aggrandizements":[{"Type":"WFCoercionVariableAggrandizement",
                                                 "CoercionItemClass":"WFStringContentItem"}]},
                     "WFSerializationType":"WFTextTokenAttachment"}},
                 "WFCondition":4, "WFConditionalActionString":mode}},
            workflow(name, mode)["WFWorkflowActions"][0],
            {"WFWorkflowActionIdentifier":"is.workflow.actions.conditional",
             "WFWorkflowActionParameters":{"GroupingIdentifier":group, "WFControlFlowMode":2}}
        ])
    # Nest both recognized values; all other input reaches the menu.
    text_action, on_if, on_action, on_end, off_if, off_action, off_end = actions
    def otherwise(begin):
        return {"WFWorkflowActionIdentifier":"is.workflow.actions.conditional",
                "WFWorkflowActionParameters":{
                    "GroupingIdentifier":begin["WFWorkflowActionParameters"]["GroupingIdentifier"],
                    "WFControlFlowMode":1}}
    actions = [text_action, on_if, on_action, otherwise(on_if),
               off_if, off_action, otherwise(off_if)]
    menu_group = "30F28665-D168-4D0E-9E7A-349B067D39C9"
    actions.append({
        "WFWorkflowActionIdentifier":"is.workflow.actions.choosefrommenu",
        "WFWorkflowActionParameters":{
            "GroupingIdentifier":menu_group, "WFControlFlowMode":0,
            "WFMenuPrompt":"Управление VPN",
            "WFMenuItems":[
                {"WFItemType":0, "WFValue":"Включить VPN"},
                {"WFItemType":0, "WFValue":"Выключить VPN"}]}})
    for mode, title in (("on", "Включить VPN"), ("off", "Выключить VPN")):
        actions.append({
            "WFWorkflowActionIdentifier":"is.workflow.actions.choosefrommenu",
            "WFWorkflowActionParameters":{
                "GroupingIdentifier":menu_group, "WFControlFlowMode":1,
                "WFMenuItemTitle":title, "WFMenuItemAttributedTitle":title}})
        actions.append(workflow(name, mode)["WFWorkflowActions"][0])
    actions.extend([
        {"WFWorkflowActionIdentifier":"is.workflow.actions.choosefrommenu",
         "WFWorkflowActionParameters":{"GroupingIdentifier":menu_group, "WFControlFlowMode":2}},
        off_end, on_end
    ])
    # Diagnostic build: remain in Shortcuts to distinguish a crash from Home Screen navigation.
    doc["WFWorkflowActions"] = actions
    return doc

def sign(raw, title):
    body = json.dumps({"shortcutName": title, "shortcut": raw.decode()}).encode()
    req = Request("https://hubsign.routinehub.services/sign", data=body,
                  headers={"Content-Type": "application/json", "User-Agent": "cherri/2.3.0"}, method="POST")
    with urlopen(req, timeout=40) as response:
        data = response.read(2_000_001)
        if response.status != 200 or not valid_signed(data):
            raise ValueError("Invalid shortcut signing response")
        return data

def valid_signed(data):
    return 2000 < len(data) <= 2_000_000 and data.startswith(b"AEA1")

def signed_shortcut(name, mode, cache=None, signer=None):
    document = controller(name) if mode == "control" else workflow(name, mode)
    raw = plistlib.dumps(document, fmt=plistlib.FMT_XML, sort_keys=False)
    key = hashlib.sha256(VERSION.encode() + raw).hexdigest()
    directory = Path(cache) if cache is not None else CACHE
    # Serialize cache misses, so repeated taps cannot flood the signing service.
    with _LOCK:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = directory / (key + ".shortcut")
        if path.exists():
            data = path.read_bytes()
            if valid_signed(data) and time.time() - path.stat().st_mtime < 7 * 86400:
                return data
        data = (signer or sign)(raw, document["WFWorkflowName"])
        if not valid_signed(data):
            raise ValueError("Invalid shortcut signing response")
        fd, temporary = tempfile.mkstemp(dir=directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return data
