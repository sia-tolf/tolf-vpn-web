import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / 'setup/anyconnect/install-riga-foundation.py'
spec = importlib.util.spec_from_file_location('riga_foundation', SOURCE)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class RigaFoundationTests(unittest.TestCase):
    def test_preserves_parallel_auth_and_routing(self):
        source = ('auth = "plain[passwd=/etc/ocserv/passwd]"\n'
                  'enable-auth = "certificate"\n'
                  'ca-cert = /etc/ocserv/client-ca.pem\nroute = default\n')
        result = installer.updated_config(source)
        self.assertTrue(result.startswith(source))
        self.assertEqual(len(installer.options(result, 'crl')), 1)
        self.assertEqual(installer.updated_config(result), result)

    def test_rejects_existing_unrelated_crl(self):
        with self.assertRaisesRegex(RuntimeError, 'CRL needs integration'):
            installer.updated_config('auth=certificate\nca-cert=/ca\ncrl=/old-crl\n')

    def test_requires_certificate_auth_and_single_ca(self):
        for source in ('auth=plain\nca-cert=/ca\n',
                       'auth=certificate\nca-cert=/ca\nca-cert=/other\n'):
            with self.assertRaises(RuntimeError):
                installer.updated_config(source)

    def test_atomic_preserves_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'file'
            target.write_bytes(b'old')
            target.chmod(0o640)
            installer.atomic(target, b'new')
            self.assertEqual(target.read_bytes(), b'new')
            self.assertEqual(target.stat().st_mode & 0o777, 0o640)

    def test_failed_ocserv_validation_restores_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conf, trust = root / 'ocserv.conf', root / 'ca.pem'
            original = 'auth=plain\nenable-auth=certificate\nca-cert=' + str(trust) + '\n'
            conf.write_text(original)
            trust.write_bytes(b'original CA\n')
            directory = root / 'tolf-uk'
            sync, service, timer = root / 'sync', root / 'sync.service', root / 'sync.timer'
            def run(*args):
                if args[0] == 'curl':
                    Path(args[-1]).write_bytes(b'public download\n')
                if args[:2] == ('ocserv', '-t'):
                    raise subprocess.CalledProcessError(1, args)
                return ''
            with patch.multiple(installer, CONF=conf, DIRECTORY=directory,
                                SYNC_PATH=sync, SERVICE=service, TIMER=timer,
                                SYNC='#!/bin/sh\nexit 0\n'), \
                 patch.object(installer, 'run', side_effect=run), \
                 patch.object(installer, 'fingerprint', return_value='a' * 64), \
                 patch.object(installer.os, 'geteuid', return_value=0), \
                 patch.object(installer.shutil, 'which', return_value='/tool'), \
                 patch.object(installer.subprocess, 'run', return_value=
                              subprocess.CompletedProcess([], 1)), \
                 patch.object(sys, 'argv', ['installer', 'a' * 64]):
                with self.assertRaises(subprocess.CalledProcessError):
                    installer.main()
            self.assertEqual(conf.read_text(), original)
            self.assertEqual(trust.read_bytes(), b'original CA\n')
            for target in (sync, service, timer, directory / 'uk-client-ca.pem',
                           directory / 'uk-client-ca.sha256'):
                self.assertFalse(target.exists(), target)


if __name__ == '__main__':
    unittest.main()
