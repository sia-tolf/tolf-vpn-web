"""Signed Cisco shortcuts using the owner's verified native intent parameters."""
import hashlib
import json
import os
import plistlib
import tempfile
import time
import threading
from pathlib import Path
from urllib.request import Request, urlopen

_LOCK = threading.Lock()
CACHE = Path("/var/lib/tolf-api/ios-shortcuts")
VERSION = "cisco-v1"

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
    document = workflow(name, mode)
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
