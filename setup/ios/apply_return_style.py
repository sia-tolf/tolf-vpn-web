"""Remove obsolete logo typography from profile-page return controls."""
from pathlib import Path
import re

def transform(source):
    # The old :last-child selector outranks .brand .return-label.
    return re.sub(r'\.brand span:last-child\{\{[^}]*\}\}', '', source)

def transform_html(content):
    return re.sub(r'\.brand span:last-child\{[^}]*\}', '', content)

if __name__ == "__main__":
    import sys
    path=Path(sys.argv[1])
    source=transform(path.read_text())
    compile(source,str(path),"exec")
    path.write_text(source)
