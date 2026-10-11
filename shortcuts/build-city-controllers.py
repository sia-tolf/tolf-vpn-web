"""Build two shared city controllers, independent of device/account names."""
import plistlib, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"setup/anyconnect"))
from tolf_oc_shortcuts import controller, sign

if __name__=="__main__":
    dest=Path(__file__).parent/"cities"
    dest.mkdir(exist_ok=True)
    for city,color in (("Москва",4282601983),("Рига",2071128575)):
        name="TOLF "+city
        doc=controller(name)
        doc["WFWorkflowIcon"]["WFWorkflowIconStartColor"]=color
        raw=plistlib.dumps(doc,fmt=plistlib.FMT_XML,sort_keys=False)
        (dest/(name+".plist")).write_bytes(raw)
        (dest/(name+".shortcut")).write_bytes(sign(raw,name))
        assert doc["WFWorkflowName"]==name
        assert not doc["WFWorkflowHasShortcutInputVariables"]
        bindings={a["WFWorkflowActionParameters"]["WFVPN"]["title"] for a in doc["WFWorkflowActions"]
            if "WFVPN" in a["WFWorkflowActionParameters"]}
        assert bindings=={name}
        print("Signed and checked:",name)
