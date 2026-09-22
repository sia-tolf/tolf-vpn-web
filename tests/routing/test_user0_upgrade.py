from contextlib import ExitStack
import builtins
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

SOURCE = Path(__file__).resolve().parents[2] / 'setup/personal-routing/user0-service'
spec = importlib.util.spec_from_file_location('user0_upgrade', SOURCE/'upgrade-receiver.py')
upgrade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upgrade)


class UpgradeTests(unittest.TestCase):
    def exercise(self, fail_health=False, changed_file=False):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            target = root/'target'
            target.mkdir()
            old = {'service.py': b'# previous service\n', 'core.py': b'# previous core\n'}
            for name, content in old.items():
                (target/name).write_bytes(content)
            expected = {name:hashlib.sha256(content).hexdigest() for name,content in old.items()}
            if changed_file:
                (target/'service.py').write_text('# user changed this\n')
            backup = root/'backup'
            backup.mkdir()
            for name, value in [('TARGET',target), ('OLD',expected), ('INIT',str(root/'init'))]:
                stack.enter_context(patch.object(upgrade,name,value))
            exists = Path.exists
            stack.enter_context(patch.object(Path,'exists',lambda p: True if str(p)=='/etc/openwrt_release' else exists(p)))
            stack.enter_context(patch.object(upgrade.os,'geteuid',return_value=0))
            original_open = builtins.open
            def fopen(path,*args,**kw):
                if str(path)=='/var/lock/tolf-user0-receiver-install.lock':
                    path=root/'lock'
                return original_open(path,*args,**kw)
            stack.enter_context(patch.object(builtins,'open',fopen))
            stack.enter_context(patch.object(upgrade.tempfile,'mkdtemp',return_value=str(backup)))
            fake = MagicMock()
            fake.policy.bootstrap.return_value={'revision':0}
            fake.policy.encoded.return_value=b'{"revision":0}'
            fake.policy.digest.return_value='initial-digest'
            fake.policy.nft_rules.return_value=''
            fake.policy.PROTOCOL=2
            stack.enter_context(patch.object(upgrade.importlib.util,'module_from_spec',return_value=fake))
            stack.enter_context(patch.object(upgrade.importlib.util,'spec_from_file_location',
                                            return_value=SimpleNamespace(loader=MagicMock())))
            stack.enter_context(patch.object(upgrade,'wait_ready',side_effect=[
                {'rule':'user0: delfi.lv -> moscow'},
                RuntimeError('new service unhealthy') if fail_health else {'policyDigest':'initial-digest'}]))
            calls=[]
            def execute(args,**kw):
                calls.append(args)
                if len(args)==2 and args[1]==str(backup/'rollback.py'):
                    runpy.run_path(args[1],run_name='__main__')
                return subprocess.CompletedProcess(args,0,stdout=json.dumps({'state':'applied','appliedRevision':0}))
            stack.enter_context(patch.object(upgrade,'run',side_effect=execute))
            stack.enter_context(patch.object(upgrade.subprocess,'run',side_effect=execute))
            if changed_file:
                with self.assertRaisesRegex(RuntimeError,'differs'):
                    upgrade.main()
                self.assertEqual(calls,[])
                self.assertEqual((target/'service.py').read_text(),'# user changed this\n')
            elif fail_health:
                with self.assertRaisesRegex(RuntimeError,'unhealthy'):
                    upgrade.main()
                self.assertEqual((target/'service.py').read_bytes(),old['service.py'])
                for name in ('policy.py','rpc.py','policy.json'):
                    self.assertFalse((target/name).exists())
                self.assertIn([str(root/'init'),'start'],calls)
            else:
                upgrade.main()
                self.assertEqual((target/'service.py').read_bytes(),(SOURCE/'service.py').read_bytes())
                self.assertEqual((backup/'service.py').read_bytes(),old['service.py'])
                self.assertTrue((backup/'rollback.py').exists())

    def test_unexpected_installed_file_is_never_overwritten(self):
        self.exercise(changed_file=True)

    def test_failed_new_service_restores_old_files(self):
        self.exercise(fail_health=True)

    def test_success_keeps_previous_service_and_rollback(self):
        self.exercise()


if __name__=='__main__':
    unittest.main()
