import datetime as dt
import importlib.util
from pathlib import Path
import tempfile
import unittest
import uuid
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("oc_certificates", ROOT / "setup/anyconnect/tolf_oc_certificates.py")
certificates = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(certificates)


class Certificates(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name) / "authority"
        self.fingerprint = certificates.initialize(self.directory)
        self.ca = certificates.Authority(self.directory)

    def tearDown(self):
        self.temp.cleanup()

    def test_authority_is_not_replaced(self):
        self.assertEqual(certificates.initialize(self.directory), self.fingerprint)
        self.assertEqual((self.directory / "ca-key.pem").stat().st_mode & 0o777, 0o600)
        with self.assertRaises(TypeError):
            serialization.load_pem_private_key((self.directory / "ca-key.pem").read_bytes(), None)

    def test_device_identity_bundle_and_signature(self):
        one = self.ca.issue(str(uuid.uuid4()))
        two = self.ca.issue(str(uuid.uuid4()))
        self.assertNotEqual(one["username"], two["username"])
        cert = x509.load_pem_x509_certificate(one["certificate"])
        self.ca.cert.public_key().verify(cert.signature, cert.tbs_certificate_bytes,
                                         padding.PKCS1v15(), cert.signature_hash_algorithm)
        self.assertFalse(cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca)
        self.assertIn(ExtendedKeyUsageOID.CLIENT_AUTH,
                      cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value)
        data, password = self.ca.bundle(one)
        key, loaded, chain = pkcs12.load_key_and_certificates(data, password.encode())
        self.assertEqual(loaded.serial_number, cert.serial_number)
        self.assertEqual(key.public_key().public_numbers(), loaded.public_key().public_numbers())
        self.assertEqual(chain[0].subject, self.ca.cert.subject)
        with self.assertRaises(ValueError):
            pkcs12.load_key_and_certificates(data, b"wrong-password")

    def test_revocation_list(self):
        record = self.ca.issue(str(uuid.uuid4()))
        crl = x509.load_pem_x509_crl(self.ca.crl([(record["serial"], certificates.now())], 2))
        self.ca.cert.public_key().verify(crl.signature, crl.tbs_certlist_bytes,
                                         padding.PKCS1v15(), crl.signature_hash_algorithm)
        self.assertIsNotNone(crl.get_revoked_certificate_by_serial_number(int(record["serial"], 16)))
        self.assertGreater(crl.next_update_utc, certificates.now())

    def test_incomplete_authority_is_not_regenerated(self):
        (self.directory / "ca-key.pem").unlink()
        with self.assertRaises(FileNotFoundError):
            certificates.initialize(self.directory)

    def test_invalid_identity(self):
        with self.assertRaises(ValueError):
            self.ca.issue("../../other")
        with self.assertRaises(ValueError):
            self.ca.issue(str(uuid.uuid4()), days=500)


if __name__ == "__main__":
    unittest.main()
