import importlib.util
from pathlib import Path
import ast
p=Path(__file__).resolve().parents[2]/'setup/install-windows-api.py'
spec=importlib.util.spec_from_file_location('installer',p);installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)

def test_patch_only_delete_and_register():
 src='''def authenticated_user_id(request): pass
def provision_on_riga(*args): pass
def remove_provisioned_vpn(*args): pass
def requested_platform(payload): return "ios"
def account_delete(request, payload=None):
    user_id = authenticated_user_id(request)
    with tolf_promos.account_operation(DB, user_id):
        row = vpn_record(user_id)
        remove_provisioned_vpn(user_id, row)
        for table in ("vpn_access", "passkeys", "sessions"):
            con.execute(table)
    return {"status":"ok"}
def vpn_create(request): return "UNCHANGED"
'''
 patched=installer.patch_main(src);ast.parse(patched)
 assert patched.index('tolf_windows.delete_all(user_id)')<patched.index('row = vpn_record(user_id)')
 assert '"windows_devices", "vpn_access"' in patched
 assert 'def vpn_create(request): return "UNCHANGED"' in patched
 try:installer.patch_main(patched)
 except RuntimeError:pass
 else:assert False,'reinstallation should not append duplicate hooks'
