import datetime as dt
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "setup/anyconnect"))
from tolf_oc_certificates import initialize, Authority, now


@unittest.skipUnless(shutil.which("openssl"), "OpenSSL needed for node validation")
class MoscowCRL(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)
        initialize(self.dir / "authority")
        self.authority = Authority(self.dir / "authority")
        (self.dir / "uk-client-ca.pem").write_bytes((self.dir / "authority/ca.pem").read_bytes())
        (self.dir / "uk-client-ca.sha256").write_text(self.authority.fingerprint + "\n")
        self.fixture = self.dir / "incoming.pem"
        self.current = self.dir / "uk-client-ca.crl.pem"
        self.calls = self.dir / "reloads"
        self.bin = self.dir / "bin"
        self.bin.mkdir()
        for name, body in {
            "curl": '#!/bin/sh\nwhile [ "$#" -gt 0 ]; do if [ "$1" = -o ]; then cp "$TOLF_TEST_CRL" "$2"; exit; fi; shift; done\nexit 1\n',
            "occtl": '#!/bin/sh\necho reload >> "$TOLF_TEST_CALLS"\n[ "${TOLF_TEST_FAIL:-0}" = 0 ]\n',
        }.items():
            path = self.bin / name
            path.write_text(body)
            path.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin) + ":" + os.environ["PATH"],
                        TOLF_OC_DIRECTORY=str(self.dir), TOLF_OC_LOCK_DIRECTORY=str(self.dir / "lock"),
                        TOLF_OC_LAST_SYNC=str(self.dir / "last-sync"),
                        TOLF_TEST_CRL=str(self.fixture), TOLF_TEST_CALLS=str(self.calls))

    def tearDown(self):
        self.temp.cleanup()

    def run_sync(self, data):
        self.fixture.write_bytes(data)
        return subprocess.run(["sh", str(ROOT / "setup/anyconnect/sync-moscow-crl.sh")],
                              env=self.env, capture_output=True, text=True)

    def test_valid_install_and_unchanged_list_do_not_repeat_reload(self):
        data = self.authority.crl([], 3)
        self.assertEqual(self.run_sync(data).returncode, 0)
        self.assertEqual(self.current.read_bytes(), data)
        self.assertEqual(self.run_sync(data).returncode, 0)
        self.assertEqual(self.calls.read_text().splitlines(), ["reload"])

    def test_old_number_and_same_number_conflict_rejected(self):
        original = self.authority.crl([], 3)
        self.current.write_bytes(original)
        self.assertNotEqual(self.run_sync(self.authority.crl([], 2)).returncode, 0)
        changed = self.authority.crl([("abc", now())], 3)
        self.assertNotEqual(self.run_sync(changed).returncode, 0)
        self.assertEqual(self.current.read_bytes(), original)
        self.assertFalse(self.calls.exists())

    def test_expired_and_foreign_signatures_rejected(self):
        expired = (x509.CertificateRevocationListBuilder().issuer_name(self.authority.cert.subject)
                   .last_update(now() - dt.timedelta(days=8)).next_update(now() - dt.timedelta(days=1))
                   .add_extension(x509.CRLNumber(2), False).sign(self.authority.key, hashes.SHA256()))
        self.assertNotEqual(self.run_sync(expired.public_bytes(serialization.Encoding.PEM)).returncode, 0)
        initialize(self.dir / "foreign")
        self.assertNotEqual(self.run_sync(Authority(self.dir / "foreign").crl([], 2)).returncode, 0)
        self.assertFalse(self.current.exists())

    def test_reload_failure_restores_previous_list(self):
        original = self.authority.crl([], 1)
        self.current.write_bytes(original)
        self.env["TOLF_TEST_FAIL"] = "1"
        self.assertNotEqual(self.run_sync(self.authority.crl([], 2)).returncode, 0)
        self.assertEqual(self.current.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
