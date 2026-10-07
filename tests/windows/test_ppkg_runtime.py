import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ppkg_verify", ROOT / "setup/windows/ppkg/verify-package.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

@pytest.fixture
def payload(tmp_path):
    data = (ROOT / "tests/windows/fixtures/native-crypto.provxml").read_text()
    (tmp_path / "runtime.provxml").write_text(data)
    return tmp_path

def test_actual_compiled_native_payload(payload):
    module.verify(payload)

def test_rejects_wrong_dh_group(payload):
    file = payload / "runtime.provxml"
    file.write_text(file.read_text().replace('value="Group14"', 'value="Group2"'))
    with pytest.raises(ValueError, match="DHGroup"):
        module.verify(payload)

def test_rejects_executable_payload(payload):
    (payload / "setup.exe").write_bytes(b"MZ")
    with pytest.raises(ValueError, match="Executable payload"):
        module.verify(payload)

def test_rejects_provisioning_commands(payload):
    file = payload / "runtime.provxml"
    file.write_text(file.read_text().replace("</wap-provisioningdoc>", '<characteristic type="ProvisioningCommands"><parm name="CommandLine" value="anything" /></characteristic></wap-provisioningdoc>'))
    with pytest.raises(ValueError, match="no other runtime providers"):
        module.verify(payload)
