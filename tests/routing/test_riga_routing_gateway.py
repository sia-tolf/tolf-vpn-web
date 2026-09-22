import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[2] / 'setup/personal-routing'
sys.path.insert(0, str(BASE / 'user0-service'))
import policy


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gateway = load('gateway_test', BASE / 'riga-gateway/gateway.py')
installer = load('gateway_installer_test', BASE / 'riga-gateway/install.py')


class GatewayTests(unittest.TestCase):
    def report(self):
        return dict(protocol=2, status='ok', node='moscow', accountId=policy.ACCOUNT,
                    vpnUsername='user0', scope='moscow-ikev2-eap-domain',
                    acceptedRevision=0, acceptedDigest=policy.digest(policy.bootstrap()))

    def test_apply_uses_stdin_and_fixed_command(self):
        with patch.object(gateway.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(self.report()).encode())) as run:
            gateway.relay('apply', policy.encoded(policy.bootstrap()))
        args, kwargs = run.call_args
        self.assertNotIn('-n', args[0])
        self.assertEqual(args[0][-1], '/usr/bin/python3 /opt/tolf-user0-routing/rpc.py apply')
        self.assertEqual(kwargs['input'], policy.encoded(policy.bootstrap()))
        self.assertFalse(kwargs.get('shell', False))

    def test_bad_account_and_command_never_run_ssh(self):
        wrong = dict(policy.bootstrap(), vpnUsername='someone_else')
        with patch.object(gateway.subprocess, 'run') as run:
            for action, body in [('apply', json.dumps(wrong).encode()), ('status; reboot', b''), ('apply', b'x' * 65537)]:
                with self.assertRaises(ValueError):
                    gateway.relay(action, body)
            run.assert_not_called()

    def test_wrong_node_or_revision_not_acknowledged(self):
        for field, value in [('node', 'riga'), ('acceptedRevision', 10), ('acceptedDigest', 'bad')]:
            report = self.report()
            report[field] = value
            with patch.object(gateway.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(report).encode())):
                with self.assertRaises(ValueError):
                    gateway.relay('apply', policy.encoded(policy.bootstrap()))

    def test_status_sends_empty_stdin(self):
        with patch.object(gateway.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(self.report()).encode())) as run:
            gateway.relay('status')
        self.assertEqual(run.call_args.kwargs['input'], b'')

    def test_shell_gate_rejects_extra_arguments_and_injection(self):
        # Substitute the privileged exec with a harmless marker, test actual bash parsing.
        block = installer.SSH_BLOCK.replace('exec sudo -n /usr/local/sbin/tolf-provision-root', 'printf "MATCH %s %s\\n"')
        for command, matched in [('personal-routing-user0 status', True), ('personal-routing-user0 apply', True),
                                  ('personal-routing-user0 apply extra', False), ('personal-routing-user0 status; id', False),
                                  ('personal-routing-user0 $(id)', False), ('personal-routing-user0 status\nid', False)]:
            result = subprocess.run(['/bin/bash', '-c', block], env={'SSH_ORIGINAL_COMMAND': command}, capture_output=True, text=True, check=True)
            self.assertEqual('MATCH' in result.stdout, matched)

    def test_patch_preserves_legacy_and_rejects_second_install(self):
        source = '#!/bin/bash\nset -euo pipefail\nexec /usr/local/sbin/tolf-old "$@"\n'
        updated = installer.patch(source, installer.ROOT_BLOCK)
        self.assertIn('exec /usr/local/sbin/tolf-old "$@"', updated)
        subprocess.run(['/bin/bash', '-n'], input=updated, text=True, check=True)
        with self.assertRaises(RuntimeError):
            installer.patch(updated, installer.ROOT_BLOCK)


class InstallerTests(unittest.TestCase):
    def test_install_and_failure_restore(self):
        for fail in (False, True):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                stage, gates = folder / 'stage', folder / 'gates'
                stage.mkdir()
                gates.mkdir()
                for name in ('gateway.py', 'install.py'):
                    shutil.copy2(BASE / 'riga-gateway' / name, stage / name)
                shutil.copy2(BASE / 'user0-service/policy.py', stage / 'policy.py')
                original = b'#!/bin/bash\nset -euo pipefail\nexec /usr/local/sbin/tolf-old "$@"\n'
                for name in ('tolf-provision-root', 'tolf-provision-ssh'):
                    (gates / name).write_bytes(original)
                backup = folder / 'backup'
                backup.mkdir()
                real_open = open
                def redirected_open(path, *args, **kwargs):
                    if path == '/var/lock/tolf-provision.lock':
                        path = folder / 'lock'
                    return real_open(path, *args, **kwargs)
                def run(args, **kwargs):
                    if fail and args[0] == str(gates / 'tolf-provision-root'):
                        raise subprocess.CalledProcessError(1, args)
                    return subprocess.CompletedProcess(args, 0)
                with patch.object(installer, 'ROOT', folder / 'installed'), patch.object(installer, 'BASE', gates), \
                     patch.object(installer, '__file__', str(stage / 'install.py')), \
                     patch.object(installer.socket, 'gethostname', return_value='EDISLV'), \
                     patch.object(installer.os, 'geteuid', return_value=0), \
                     patch.object(installer.tempfile, 'mkdtemp', return_value=str(backup)), \
                     patch('builtins.open', side_effect=redirected_open), \
                     patch.object(installer.subprocess, 'run', side_effect=run):
                    if fail:
                        with self.assertRaises(subprocess.CalledProcessError):
                            installer.main()
                        self.assertFalse((folder / 'installed').exists())
                        for path in gates.iterdir():
                            self.assertEqual(path.read_bytes(), original)
                    else:
                        installer.main()
                        self.assertTrue((folder / 'installed/gateway.py').exists())
                        compile((backup / 'rollback.py').read_text(), 'rollback.py', 'exec')
                        for path in gates.iterdir():
                            self.assertIn(installer.MARKER.encode(), path.read_bytes())


if __name__ == '__main__':
    unittest.main()
