"""Build the signed controller from the production generator."""
import plistlib
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "setup/anyconnect"))
from tolf_oc_shortcuts import controller, sign

if __name__ == "__main__":
    doc = controller("TOLF Москва iPhone")
    raw = plistlib.dumps(doc, fmt=plistlib.FMT_XML, sort_keys=False)
    target = Path(__file__).parent / "auto-install"
    (target / "TOLF.plist").write_bytes(raw)
    (target / "TOLF.shortcut").write_bytes(sign(raw, "TOLF"))
    print("Signed controller TOLF")
