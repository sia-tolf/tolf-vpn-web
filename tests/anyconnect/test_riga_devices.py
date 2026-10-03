import importlib.util
import base64
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2] / 'setup/anyconnect'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


devices = load('riga_devices', 'riga-devices.py')
installer = load('riga_devices_installer', 'install-riga-devices.template.py')
CN = 'tolf-oc-' + 'a' * 32


class RigaDeviceTests(unittest.TestCase):
    def test_dns_covers_other_devices_and_domain_boundaries(self):
        source = ('2026-10-03 12:00:00 CR 10.19.0.42:53000 example.ru./IN/A\n'
                  ';; ANSWER SECTION:\nexample.ru. 60 IN A 8.8.8.8\n'
                  '2026-10-03 12:00:01 CR 10.19.0.85:53001 video.googlevideo.com./IN/A\n'
                  ';; ANSWER SECTION:\nvideo.googlevideo.com. 90 IN A 1.1.1.1\n'
                  '2026-10-03 12:00:02 CR 10.21.0.42:53000 example.ru./IN/A\n'
                  ';; ANSWER SECTION:\nexample.ru. 60 IN A 9.9.9.9\n')
        result = devices.parse_dns(source, 100)
        self.assertEqual(result['ru_domains4'], {'8.8.8.8': 160})
        self.assertEqual(result['yt_domains4'], {'1.1.1.1': 190})
        self.assertIsNone(devices.dns_kind('notyoutube.com'))
        self.assertIsNone(devices.dns_kind('youtube.com.attacker.example'))

    def test_reprocessing_history_does_not_extend_ttl(self):
        source = ('12:00:00 CR 10.19.0.42:53000 example.ru./IN/A\n'
                  ';; ANSWER SECTION:\nexample.ru. 60 IN A 8.8.8.8\n')
        seen = {}
        devices.parse_dns(source, 100, observed=seen)
        result = devices.parse_dns(source, 200, seen=seen)
        self.assertEqual(result['ru_domains4']['8.8.8.8'], 160)
        fresh = devices.parse_dns(source.replace('12:00:00', '12:02:00'), 200, seen=seen)
        self.assertEqual(fresh['ru_domains4']['8.8.8.8'], 260)

    def test_rules_expire_answers_and_isolate_pilot_table(self):
        result = devices.rules('8.8.8.0/24\n', [(CN, '1', '10.19.0.42', 'yt')],
                               {'yt_domains4': {'1.1.1.1': 101, '9.9.9.9': 99}}, 100)
        self.assertIn('elements = { 1.1.1.1 }', result)
        self.assertNotIn('9.9.9.9', result)
        self.assertNotIn('tolf_oc_sr', result)
        self.assertIn('ip saddr @device_yt ip daddr @yt_domains4 meta mark set 0x192', result)
        with self.assertRaises(ValueError):
            devices.rules('8.8.8.0/24', [(CN, '1', '10.21.0.42', 'ru')], {}, 100)

    def test_unknown_identity_is_denied_and_ip_reuse_clears_stale_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime, directory = root / 'runtime', root / 'directory'
            runtime.mkdir()
            (directory / 'device-modes').mkdir(parents=True)
            stale = runtime / (CN + '.1')
            stale.write_text('10.19.0.42')
            with patch.multiple(devices, RUNTIME=runtime, DIRECTORY=directory), \
                 patch.object(devices, 'apply') as apply, \
                 patch.dict(devices.os.environ, USERNAME=CN, ID='2', IP_REMOTE='10.19.0.42', REASON='connect'):
                with self.assertRaisesRegex(RuntimeError, 'not registered'):
                    devices.hook()
                self.assertFalse(stale.exists())
                self.assertTrue((runtime / (CN + '.2')).exists())
                apply.assert_called_once()
            with patch.multiple(devices, RUNTIME=runtime, DIRECTORY=directory), \
                 patch.object(devices, 'apply'), \
                 patch.dict(devices.os.environ, USERNAME='pilot', ID='3', IP_REMOTE='10.19.0.42', REASON='connect'):
                devices.hook()
                self.assertEqual(devices.bindings(), [])

    def test_missing_and_conflicting_policy_rules_are_not_healthy(self):
        with patch.object(devices, 'run', return_value=subprocess.CompletedProcess([], 0, '[]')):
            with self.assertRaisesRegex(RuntimeError, 'missing'):
                devices.policy_rules()
        row = '[{"priority":1017,"fwmark":"0x190","table":119}]'
        with patch.object(devices, 'run', return_value=subprocess.CompletedProcess([], 0, row)):
            with self.assertRaisesRegex(RuntimeError, 'conflict'):
                devices.policy_rules(create=True)

    def test_installer_retains_existing_auth_and_refuses_unrelated_hooks(self):
        source = 'auth = plain\nenable-auth = certificate\nroute = default\n'
        result = installer.updated_config(source)
        self.assertTrue(result.startswith(source))
        self.assertEqual(installer.updated_config(result), result)
        with self.assertRaisesRegex(RuntimeError, 'needs integration'):
            installer.updated_config(source + 'connect-script = /existing-hook\n')

    def test_failed_config_validation_restores_installed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / 'public'
            directory.mkdir()
            conf, zone = root / 'ocserv.conf', root / 'ru.zone'
            source = ('auth=plain\nenable-auth=certificate\nipv4-network=10.19.0.0\n'
                      'crl=' + str(directory / 'uk-client-ca.crl.pem') + '\n')
            conf.write_text(source)
            zone.write_text('8.8.8.0/24\n')
            data = b'#!/usr/bin/python3\npass\n'
            payload = {name: {'data': base64.b64encode(data).decode(),
                             'sha256': hashlib.sha256(data).hexdigest()}
                       for name in ('riga-devices.py', 'riga-remote.py')}
            def run(*args):
                if args[:2] == ('ocserv', '-t'):
                    raise subprocess.CalledProcessError(1, args)
                return '[]' if args[0] in ('ip', 'occtl') else ''
            changed = {name: root / name.lower() for name in
                       ('CONTROLLER', 'REMOTE', 'HOOK', 'SERVICE', 'REFRESH', 'TIMER')}
            with patch.multiple(installer, CONF=conf, DIRECTORY=directory,
                                PROFILES=root / 'profiles', RUNTIME=root / 'runtime',
                                ZONE=zone, PAYLOAD=payload, **changed), \
                 patch.object(installer, 'run', side_effect=run), \
                 patch.object(installer.os, 'geteuid', return_value=0), \
                 patch.object(installer.shutil, 'which', return_value='/tool'), \
                 patch.object(installer.subprocess, 'run', return_value=
                              subprocess.CompletedProcess([], 1, '')):
                with self.assertRaises(subprocess.CalledProcessError):
                    installer.main()
            self.assertEqual(conf.read_text(), source)
            for target in changed.values():
                self.assertFalse(target.exists(), target)


if __name__ == '__main__':
    unittest.main()
