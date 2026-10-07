"""Check the compiled payload, not just the source customization."""
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

CRYPTO = {
    "AuthenticationTransformConstants": "SHA256128",
    "CipherTransformConstants": "AES256",
    "PfsGroup": "None",
    "DHGroup": "Group14",
    "IntegrityCheckMethod": "SHA256",
    "EncryptionMethod": "AES256",
}

def verify(root):
    files = list(root.rglob("*"))
    for path in files:
        if path.is_file() and path.suffix.lower() in {".exe", ".dll", ".ps1", ".cmd", ".bat", ".vbs", ".js", ".msi"}:
            raise ValueError("Executable payload found: " + path.name)
    found = set()
    for path in files:
        if path.suffix.lower() != ".xml":
            continue
        try:
            document = ET.parse(path)
        except ET.ParseError:
            continue
        for node in document.iter():
            # Windows provisioning payload contains characteristic type URIs
            # and parm name/value pairs; SyncML also uses LocURI/Data.
            encoded = ET.tostring(node, encoding="unicode")
            for key, value in CRYPTO.items():
                uri = "/NativeProfile/CryptographySuite/" + key
                if uri in encoded and value in encoded:
                    found.add(key)
    missing = set(CRYPTO) - found
    if missing:
        raise ValueError("Missing compiled native crypto settings: " + ", ".join(sorted(missing)))
    print("PASS: compiled native crypto URIs and values; no executable or script payload")
    for key, value in CRYPTO.items():
        print(key + "=" + value)

if __name__ == "__main__":
    verify(Path(sys.argv[1]))
