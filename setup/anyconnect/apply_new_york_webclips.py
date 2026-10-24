"""Enable prepared New York WebClips in the catalog-aware installed generator."""
from pathlib import Path
def patch(source):
    for field in ("entry_id", "ingress"):
        old = field + " not in LEGACY"
        new = field + ' not in (*LEGACY, "us")'
        if old in source:
            source = source.replace(old, new)
        elif new not in source:
            raise ValueError("Unknown catalog WebClip guard: " + field)
    compile(source, "<mobileconfig>", "exec")
    return source
if __name__ == "__main__":
    import sys
    path = Path(sys.argv[1])
    path.write_text(patch(path.read_text()))
