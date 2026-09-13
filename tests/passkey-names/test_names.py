import ast
import base64
import contextlib
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import types
import unittest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location("installer", "setup/passkey-names/update-passkey-names-v1.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
module = types.ModuleType("names")
exec(installer.MODULE, module.__dict__)

class Names(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "test.db")
        with sqlite3.connect(self.db) as con:
            con.execute("CREATE TABLE passkeys(credential_id BLOB PRIMARY KEY,user_id TEXT,name TEXT,public_key BLOB,sign_count INTEGER)")
            con.execute("INSERT INTO passkeys VALUES(?,?,?,?,?)",(b"credential","owner","Old",b"public",9))
        self.user = "owner"
        app = FastAPI()
        module.install(app, {"DB":self.db,"ORIGIN":"https://vpn.tolf.is","authenticated_user_id":lambda r:self.user,
            "tolf_promos":types.SimpleNamespace(account_operation=lambda *args:contextlib.nullcontext())})
        self.client = TestClient(app)
        self.key = base64.urlsafe_b64encode(b"credential").rstrip(b"=").decode()
    def rename(self, **kw):
        return self.client.post("/passkeys/rename", json={"id":self.key,"passkeyName":"Ирина — iPad",**kw},headers={"Origin":"https://vpn.tolf.is"})
    def test_rename_preserves_credentials(self):
        self.assertEqual(self.rename().status_code,200)
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute("SELECT * FROM passkeys").fetchone(),(b"credential","owner","TOLF · Ирина — iPad",b"public",9))
    def test_owner_and_origin(self):
        self.user="other"
        self.assertEqual(self.rename().status_code,404)
        self.user="owner"
        self.assertEqual(self.client.post("/passkeys/rename",json={"id":self.key,"passkeyName":"x"}).status_code,403)
    def test_validation(self):
        for value in ("", " "*3, "x"*81, "x\u202ey", "x\ny", None, 42):
            self.assertEqual(self.rename(passkeyName=value).status_code,400)
        self.assertEqual(self.rename(id="!invalid").status_code,400)
        self.assertEqual(module.label({"passkeyName":"TOLF · Office"}),"TOLF · Office")
    def test_patch_preserves_finish_and_user_handle(self):
        source = '''
@app.post("/passkey/register/begin")
def passkey_register_begin():
    user_id = "unchanged"
    webauthn_user_id = secrets.token_bytes(32)
    passkey_name = "TOLF Passkey #1"
    return webauthn_user_id, passkey_name
@app.post("/passkeys/add/begin")
def passkeys_add_begin(request: Request):
    try:
        webauthn_user_id = row[0]
        rows = con.execute("SELECT name FROM passkeys WHERE user_id=?", (user_id,)).fetchall()
        passkey_name = "TOLF Passkey #2"
    finally:
        con.close()
    return webauthn_user_id, passkey_name
async def passkey_register_finish(request: Request):
    return "original finish"
'''
        updated = installer.patch(source)
        ast.parse(updated)
        self.assertEqual(installer.patch(updated),updated)
        self.assertIn('webauthn_user_id = secrets.token_bytes(32)',updated)
        self.assertIn('webauthn_user_id = row[0]',updated)
        self.assertIn('return "original finish"',updated)
        self.assertEqual(updated.count("tolf_passkey_names.label(payload)"),2)

if __name__ == "__main__":
    unittest.main()
