from contextlib import contextmanager
import importlib
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import datetime as dt
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "setup/anyconnect"))
certificates = importlib.import_module("tolf_oc_certificates")
api = importlib.import_module("tolf_anyconnect")


class ApiFoundation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.db = self.directory / "tolf.db"
        with sqlite3.connect(self.db) as con:
            con.execute("CREATE TABLE users (id TEXT PRIMARY KEY)")
            con.executemany("INSERT INTO users VALUES (?)", [("owner",), ("other",)])
        certificates.initialize(self.directory / "anyconnect")
        def authenticate(request):
            owner = request.cookies.get("test-session")
            if owner not in ("owner", "other"):
                raise HTTPException(401, "Not authenticated")
            return owner
        self.app = FastAPI()
        api.install(self.app, {"DB": str(self.db), "ORIGIN": "https://vpn.tolf.is",
                               "authenticated_user_id": authenticate, "tolf_promos": object()})
        self.client = TestClient(self.app)

    def tearDown(self):
        self.temp.cleanup()

    def test_never_issue_before_node_activation(self):
        data = self.client.get("/oc/access/capabilities").json()
        self.assertFalse(data["issuance"])
        self.assertFalse(data["nodeReady"])
        self.assertEqual(len(data["caSha256"]), 64)
        self.assertEqual(self.client.post("/oc/access/devices").status_code, 401)
        self.client.cookies.set("test-session", "owner")
        self.assertEqual(self.client.post("/oc/access/devices").status_code, 403)
        response = self.client.post("/oc/access/devices", headers={"Origin": "https://vpn.tolf.is"})
        self.assertEqual(response.status_code, 503)

    def test_public_ca_never_includes_private_key(self):
        body = self.client.get("/oc/access/ca.pem").content
        self.assertIn(b"BEGIN CERTIFICATE", body)
        self.assertNotIn(b"PRIVATE KEY", body)

    def test_crl_is_signed_cached_and_keeps_revocations(self):
        response = self.client.get("/oc/access/crl.pem")
        self.assertEqual(response.status_code, 200)
        first = x509.load_pem_x509_crl(response.content)
        authority = certificates.Authority(self.directory / "anyconnect")
        self.assertTrue(first.is_signature_valid(authority.cert.public_key()))
        self.assertEqual(self.client.get("/oc/access/crl.pem").content, response.content)
        with sqlite3.connect(self.db) as con:
            con.execute("""INSERT INTO oc_devices
                (id,user_id,request_id,label,username,serial,certificate,encrypted_key,
                 created_at,expires_at,state,revoked_at)
                VALUES ('revoked','owner','request','iPad','tolf-oc-revoked','abc',X'01',X'02',
                        '2026-10-02','2027-10-02','revoking','2026-10-02T00:00:00+00:00')""")
        second_response = self.client.get("/oc/access/crl.pem")
        second = x509.load_pem_x509_crl(second_response.content)
        self.assertTrue(second.is_signature_valid(authority.cert.public_key()))
        self.assertIsNotNone(second.get_revoked_certificate_by_serial_number(0xabc))
        self.assertEqual(second.extensions.get_extension_for_class(x509.CRLNumber).value.crl_number,
                         first.extensions.get_extension_for_class(x509.CRLNumber).value.crl_number + 1)
        with sqlite3.connect(self.db) as con:
            con.execute("DELETE FROM oc_devices")
        self.assertEqual(self.client.get("/oc/access/crl.pem").content, second_response.content)
        self.assertNotIn(b"PRIVATE KEY", second_response.content)

    def test_corrupt_crl_is_not_replaced(self):
        path = self.directory / "anyconnect/ca.crl.pem"
        path.write_bytes(b"corrupt")
        self.assertEqual(self.client.get("/oc/access/crl.pem").status_code, 503)
        self.assertEqual(path.read_bytes(), b"corrupt")

    def test_expired_crl_is_renewed(self):
        authority = certificates.Authority(self.directory / "anyconnect")
        now = certificates.now()
        expired = (x509.CertificateRevocationListBuilder().issuer_name(authority.cert.subject)
                   .last_update(now - dt.timedelta(days=8)).next_update(now - dt.timedelta(days=1))
                   .add_extension(x509.CRLNumber(4), False).sign(authority.key, hashes.SHA256()))
        (self.directory / "anyconnect/ca.crl.pem").write_bytes(expired.public_bytes(serialization.Encoding.PEM))
        response = self.client.get("/oc/access/crl.pem")
        self.assertEqual(response.status_code, 200)
        renewed = x509.load_pem_x509_crl(response.content)
        self.assertGreater(renewed.next_update_utc, now + dt.timedelta(days=6))
        self.assertEqual(renewed.extensions.get_extension_for_class(x509.CRLNumber).value.crl_number, 5)

    def test_account_deletion_keeps_revocation_tombstone(self):
        with sqlite3.connect(self.db) as con:
            con.execute("PRAGMA foreign_keys=ON")
            con.execute("""
                INSERT INTO oc_devices
                (id,user_id,request_id,label,username,serial,certificate,encrypted_key,
                 created_at,expires_at,state)
                VALUES ('device','owner','request','iPad','tolf-oc-device','abc',X'01',X'02',
                        '2026-10-02','2027-10-02','active')
            """)
        self.assertEqual(self.client.get("/oc/access/devices").status_code, 401)
        self.client.cookies.set("test-session", "other")
        self.assertEqual(self.client.get("/oc/access/devices").json()["devices"], [])
        self.client.cookies.set("test-session", "owner")
        record = self.client.get("/oc/access/devices").json()["devices"][0]
        self.assertNotIn("encrypted_key", record)
        self.assertNotIn("certificate", record)
        with sqlite3.connect(self.db) as con:
            con.execute("PRAGMA foreign_keys=ON")
            con.execute("DELETE FROM users WHERE id='owner'")
            state, revoked_at = con.execute("SELECT state,revoked_at FROM oc_devices").fetchone()
            self.assertEqual(state, "revoking")
            self.assertIsNotNone(revoked_at)


if __name__ == "__main__":
    unittest.main()
