"""Build public city controllers with invariant English names and localized menus."""
import argparse
import plistlib
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "setup/anyconnect"))
from tolf_oc_shortcuts import controller, sign

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", choices=("ru", "en", "lv"), required=True)
    args = parser.parse_args()
    dest = Path(__file__).parent / "cities" / args.lang
    dest.mkdir(parents=True, exist_ok=True)
    for city, color in (("Moscow", 4282601983), ("Riga", 2071128575)):
        name = "TOLF " + city
        doc = controller(name, args.lang)
        doc["WFWorkflowIcon"]["WFWorkflowIconStartColor"] = color
        raw = plistlib.dumps(doc, fmt=plistlib.FMT_XML, sort_keys=False)
        assert doc["WFWorkflowName"] == name
        assert not doc["WFWorkflowHasShortcutInputVariables"]
        bindings = {a["WFWorkflowActionParameters"]["WFVPN"]["title"]
                    for a in doc["WFWorkflowActions"] if "WFVPN" in a["WFWorkflowActionParameters"]}
        assert bindings == {name}
        (dest / (name + ".plist")).write_bytes(raw)
        (dest / (name + ".shortcut")).write_bytes(sign(raw, name))
        print("Signed and checked:", args.lang, name, flush=True)
