"""The updater must accept the deployed 2.6 routing module and its own installed payload."""
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
    baseline = (ROOT / 'setup/windows/compat-2.6/tolf_windows.py').read_bytes()
    assert expected == {hashlib.sha256(baseline).hexdigest()}
    # Idempotent reinstallation accepts only this build's verified payload too.
    assert "HASHES.get('tolf_windows.py')" in template.read_text()
