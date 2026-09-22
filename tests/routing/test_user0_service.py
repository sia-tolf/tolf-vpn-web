import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from contextlib import ExitStack

SOURCE = Path(__file__).resolve().parents[2] / 'setup/personal-routing/user0-service/service.py'
spec = importlib.util.spec_from_file_location('user0_service', SOURCE)
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)
install_spec = importlib.util.spec_from_file_location('user0_install', SOURCE.with_name('install.py'))
installer = importlib.util.module_from_spec(install_spec)
install_spec.loader.exec_module(installer)


class ServiceTests(unittest.TestCase):
    def test_refuses_foreign_table(self):
        outputs = [
            {'nftables': [{'table': {'family': 'inet', 'name': service.core.TABLE}}]},
            {'nftables': [{'table': {'family': 'inet', 'name': service.core.TABLE, 'comment': 'other'}}]},
        ]
        with patch.object(service.core, 'command', side_effect=[
                subprocess.CompletedProcess([], 0, stdout=json.dumps(v)) for v in outputs]):
            with self.assertRaisesRegex(RuntimeError, 'ownership'):
                service.owned_table()

    def test_recovery_rejects_addresses_outside_user_pool(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(service, 'RUNTIME', Path(directory)):
            (Path(directory) / 'addresses.json').write_text('["192.168.200.1"]')
            with self.assertRaises(ValueError):
                service.remembered_addresses()

    def test_moscow_route_gate_rejects_riga(self):
        with patch.object(service.core, 'command', return_value=subprocess.CompletedProcess(
                [], 0, stdout='104.20.18.136 dev gre4-riga_gre table 100')):
            with self.assertRaises(RuntimeError):
                service.check_route()

    def test_dns_probe_rejects_servfail(self):
        response = b'aa' + struct.pack('!HHHHH', 0x8182, 1, 0, 0, 0)
        with patch.object(service.os, 'urandom', return_value=b'aa'), patch.object(service.socket, 'socket') as s:
            s.return_value.__enter__.return_value.recv.return_value = response
            with self.assertRaises(RuntimeError):
                service.dns_alive(53)

    def exercise_failure(self, *, worker_exits=False, cleanup_fails=False):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            stack.enter_context(patch.object(service, 'RUNTIME', Path(directory)))
            stack.enter_context(patch.object(service, 'STOP', False))
            for name in ('check_route', 'dns_alive'):
                stack.enter_context(patch.object(service, name))
            stack.enter_context(patch.object(service, 'owned_table', return_value=True))
            stack.enter_context(patch.object(service.socket, 'socket'))
            stack.enter_context(patch.object(service.time, 'sleep'))
            stack.enter_context(patch.object(service.core, 'command'))
            stack.enter_context(patch.object(service.core, 'nft'))
            stack.enter_context(patch.object(service.core, 'read_bindings', side_effect=RuntimeError('VICI down')))
            clean = stack.enter_context(patch.object(service.core, 'cleanup',
                side_effect=RuntimeError('cleanup failure') if cleanup_fails else None))
            worker = MagicMock()
            worker.poll.return_value = 1 if worker_exits else None
            stack.enter_context(patch.object(service.subprocess, 'Popen', return_value=worker))
            with self.assertRaises(RuntimeError):
                service.run_service()
            clean.assert_called_once()
            if not worker_exits:
                worker.terminate.assert_called_once()
                worker.wait.assert_called_once()
            self.assertFalse((Path(directory) / 'status.json').exists())
            conf = (Path(directory) / 'dnsmasq.conf').read_text()
            self.assertIn('pid-file=' + directory + '/dnsmasq.pid', conf)

    def test_vici_failure_withdraws_rules_and_stops_private_dns(self):
        self.exercise_failure()

    def test_dns_exit_withdraws_rules(self):
        self.exercise_failure(worker_exits=True)

    def test_cleanup_failure_still_reaps_dns_worker(self):
        self.exercise_failure(cleanup_fails=True)

    def test_parent_death_setup_failure_exits_child(self):
        with patch.object(service.ctypes, 'CDLL') as libc, patch.object(service.os, '_exit', side_effect=SystemExit) as quit:
            libc.return_value.prctl.return_value = -1
            with self.assertRaises(SystemExit):
                service.die_with_parent(10)
            quit.assert_called_once_with(125)


class InstallerTests(unittest.TestCase):
    def exercise(self, fail_start):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            target = root / 'target'
            init = root / 'init'
            status = root / 'status.json'
            for name, value in [('TARGET', target), ('INIT', init), ('STATUS', status)]:
                stack.enter_context(patch.object(installer, name, value))
            original_exists = Path.exists
            stack.enter_context(patch.object(Path, 'exists', lambda p: True if str(p) == '/etc/openwrt_release' else original_exists(p)))
            stack.enter_context(patch.object(installer.os, 'geteuid', return_value=0))
            stack.enter_context(patch.object(installer.os, 'kill'))
            stack.enter_context(patch.object(installer.shutil, 'which', return_value='/bin/mock'))
            stack.enter_context(patch.object(installer.socket, 'socket'))
            fake = MagicMock()
            fake.owned_table.return_value = False
            fake.core.input_rules.return_value = []
            fake.core.PORT = 1053
            stack.enter_context(patch.object(installer.importlib.util, 'module_from_spec', return_value=fake))
            stack.enter_context(patch.object(installer.importlib.util, 'spec_from_file_location',
                                             return_value=SimpleNamespace(loader=MagicMock())))
            calls = []
            def command(args, **kw):
                calls.append(args)
                if args == [str(init), 'start']:
                    if fail_start:
                        raise RuntimeError('start failed')
                    status.write_text(json.dumps({'pid': 123, 'updated': installer.time.time()}))
                if args == [str(init), 'enable']:
                    self.assertTrue(status.exists())
                return subprocess.CompletedProcess(args, 0)
            stack.enter_context(patch.object(installer, 'run', side_effect=command))
            stack.enter_context(patch.object(installer.subprocess, 'run', side_effect=command))
            if fail_start:
                with self.assertRaisesRegex(RuntimeError, 'start failed'):
                    installer.main()
                self.assertFalse(target.exists())
                self.assertFalse(init.exists())
                self.assertIn([str(init), 'stop'], calls)
                self.assertIn(['/usr/bin/python3', str(target / 'service.py'), '--cleanup'], calls)
                self.assertNotIn([str(init), 'enable'], calls)
            else:
                installer.main()
                self.assertTrue((target / 'service.py').exists())
                self.assertTrue(init.exists())
                self.assertIn([str(init), 'enable'], calls)

    def test_failed_install_rolls_back_only_new_files(self):
        self.exercise(True)

    def test_autostart_enabled_only_after_fresh_status(self):
        self.exercise(False)


if __name__ == '__main__':
    unittest.main()
