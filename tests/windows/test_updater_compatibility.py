"""The updater must accept the shipped 2.0 module and its own installed payload."""
import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_supported_native_modules():
    template = ROOT / 'setup/windows/update-template.py'
    tree = ast.parse(template.read_text(encoding='utf-8'))
    expected = next(ast.literal_eval(node.value) for node in tree.body
                    if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'EXPECTED' for t in node.targets))
    # Exact normalized bytes shipped from e346834e1263484d615e152e403917a491940371.
    assert '9fbc3ab4fb493b4d386e29c1eac5c340ff6f22fa4fb3544521e178a010112c3c' in expected
    payload = (ROOT / 'setup/windows/tolf_windows.py').read_bytes().replace(b'\r\n', b'\n')
    assert hashlib.sha256(payload).hexdigest() in expected
