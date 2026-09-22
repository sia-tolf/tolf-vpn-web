import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import subprocess
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[2] / 'setup/personal-routing'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

contract = load('tolf_routing_contract', BASE / 'user0-service/policy.py')
delivery = load('tolf_routing_delivery', BASE / 'uk-delivery/tolf_routing_delivery.py')
api = load('delivery_api_test', BASE / 'uk-delivery/tolf_personal_routing.py')
installer = load('delivery_install_test', BASE / 'uk-delivery/install.py')


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = str(Path(self.temp.name) / 'test.db')
        with sqlite3.connect(self.db) as con:
            con.executescript('CREATE TABLE users(id TEXT PRIMARY KEY); CREATE TABLE vpn_access(user_id TEXT PRIMARY KEY,vpn_username TEXT);')
            con.execute('INSERT INTO users VALUES (?)', (contract.ACCOUNT,))
            con.execute('INSERT INTO users VALUES (?)', ('bob',))
            con.execute('INSERT INTO vpn_access VALUES (?,?)', (contract.ACCOUNT, 'user0'))
            con.execute('INSERT INTO vpn_access VALUES (?,?)', ('bob', 'vpn_bob'))
        api.initialize(self.db)
        delivery.initialize(self.db)
        api.save_policy(self.db, contract.ACCOUNT, {'revision': 0, 'routingRules': {'moscow':['delfi.lv']}})
        with sqlite3.connect(self.db) as con:
            con.execute('INSERT INTO vpn_personal_routing_delivery(account_id,enabled) VALUES (?,1)', (contract.ACCOUNT,))
        self.remote = contract.bootstrap()
        self.calls = []
        self.state = 'applied'

    def report(self, intent):
        return dict(protocol=2,status='ok',node='moscow',accountId=contract.ACCOUNT,
                    vpnUsername='user0',scope='moscow-ikev2-eap-domain',
                    acceptedRevision=intent['revision'],acceptedDigest=contract.digest(intent),
                    appliedRevision=intent['revision'],appliedDigest=contract.digest(intent),state=self.state)

    def rpc(self, action, intent=None):
        self.calls.append(action)
        if action == 'apply':
            self.remote = intent
        return self.report(self.remote)

    def tick(self):
        delivery.cycle(self.db, self.rpc)
        return api.get_policy(self.db, contract.ACCOUNT)

    def test_delivered_then_idempotent_poll(self):
        self.assertEqual(self.tick()['appliedRevision'], 1)
        self.tick()
        self.assertEqual(self.calls, ['status','apply','status'])

    def test_node_offline_then_recovers(self):
        delivery.cycle(self.db, lambda *a: (_ for _ in ()).throw(OSError('offline')))
        result = api.get_policy(self.db, contract.ACCOUNT)
        self.assertEqual(result['state'], 'unavailable')
        self.assertIsNone(result['appliedRevision'])
        self.assertEqual(self.tick()['state'], 'applied')

    def test_old_ack_not_shown_after_api_save(self):
        self.tick()
        api.save_policy(self.db, contract.ACCOUNT, {'revision':1,'routingRules':{'riga':['example.com']}})
        self.assertIsNone(api.get_policy(self.db, contract.ACCOUNT)['appliedRevision'])
        self.assertEqual(self.tick()['appliedRevision'], 2)

    def test_update_while_rpc_running_rejects_late_ack(self):
        def racing(action, intent=None):
            result = self.rpc(action, intent)
            if action == 'apply':
                api.save_policy(self.db, contract.ACCOUNT, {'revision':1,'routingRules':{'riga':['example.com']}})
            return result
        delivery.cycle(self.db, racing)
        self.assertIsNone(api.get_policy(self.db, contract.ACCOUNT)['appliedRevision'])
        self.assertEqual(self.tick()['appliedRevision'], 2)

    def test_deleted_vpn_withdraws_and_recreated_uses_monotonic_node_revision(self):
        self.tick()
        with sqlite3.connect(self.db) as con:
            con.execute('DELETE FROM vpn_access WHERE user_id=?', (contract.ACCOUNT,))
        delivery.cycle(self.db, self.rpc)
        self.assertEqual(self.remote['routingRules'], delivery.EMPTY)
        self.assertEqual(self.remote['revision'], 2)
        with sqlite3.connect(self.db) as con:
            con.execute('INSERT INTO vpn_access VALUES (?,?)', (contract.ACCOUNT,'user0'))
        self.assertEqual(self.tick()['appliedRevision'], 1)
        self.assertEqual(self.remote['revision'], 3)

    def test_duplicate_owner_withdraws(self):
        self.tick()
        with sqlite3.connect(self.db) as con:
            con.execute("UPDATE vpn_access SET vpn_username='user0' WHERE user_id='bob'")
        delivery.cycle(self.db, self.rpc)
        self.assertEqual(self.remote['routingRules'], delivery.EMPTY)

    def test_clear_rule_delivered(self):
        self.tick()
        api.save_policy(self.db, contract.ACCOUNT, {'revision':1,'routingRules':{}})
        self.assertEqual(self.tick()['state'], 'applied')
        self.assertEqual(self.remote['routingRules'], delivery.EMPTY)

    def test_conflict_and_no_session(self):
        self.state = 'conflict'
        result = self.tick()
        self.assertEqual(result['state'], 'conflict')
        self.assertIsNone(result['appliedRevision'])
        self.state = 'ready'
        self.assertEqual(self.tick()['state'], 'ready')

    def test_freshness_and_digest(self):
        self.tick()
        with sqlite3.connect(self.db) as con:
            con.execute('UPDATE vpn_personal_routing_delivery SET observed_at=?', (time.time()-70,))
        self.assertEqual(api.get_policy(self.db, contract.ACCOUNT)['state'], 'unavailable')
        self.tick()
        with sqlite3.connect(self.db) as con:
            bad = self.report(self.remote)
            bad['appliedDigest'] = 'bad'
            con.execute('UPDATE vpn_personal_routing_delivery SET observed_json=?', (json.dumps(bad),))
        self.assertIsNone(api.get_policy(self.db, contract.ACCOUNT)['appliedRevision'])

    def test_ahead_node_never_overwritten(self):
        self.remote = dict(self.remote,revision=99)
        result = self.tick()
        self.assertEqual(self.calls, ['status'])
        self.assertEqual(result['state'], 'unavailable')

    def test_other_user_storage_only(self):
        api.save_policy(self.db, 'bob', {'revision':0, 'routingRules':{'riga':['example.com']}})
        self.tick()
        self.assertFalse(api.get_policy(self.db,'bob')['enforcementAvailable'])
        self.assertNotIn('example.com', json.dumps(self.remote))

    def test_installer_success_and_rollback_after_start_failure(self):
        for fail in (False, True):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                root, stage = folder / 'api', folder / 'stage'
                root.mkdir()
                stage.mkdir()
                original = (BASE / 'tolf_personal_routing.py').read_bytes()
                target = root / 'tolf_personal_routing.py'
                target.write_bytes(original)
                (root / 'main.py').write_text('test')
                for source_path in (BASE / 'uk-delivery').glob('*.py'):
                    shutil.copy2(source_path, stage / source_path.name)
                shutil.copy2(BASE / 'user0-service/policy.py', stage / 'tolf_routing_contract.py')
                db = folder / 'db'
                with sqlite3.connect(self.db) as old, sqlite3.connect(db) as con:
                    old.backup(con)
                    con.execute('DROP TABLE vpn_personal_routing_delivery')
                    con.execute('UPDATE vpn_personal_routing SET rules_json=?', (json.dumps(installer.OLD_RULES),))
                unit = folder / 'delivery.service'
                self.remote = contract.bootstrap()
                real_open = open
                def local_open(path, *args, **kwargs):
                    if path == '/var/lock/tolf-personal-routing-install.lock':
                        path = folder / 'install.lock'
                    return real_open(path, *args, **kwargs)
                def command(args, **kwargs):
                    if args[:2] == ['systemctl','enable']:
                        if fail:
                            raise subprocess.CalledProcessError(1,args)
                        delivery.cycle(str(db),self.rpc)
                    return subprocess.CompletedProcess(args,0,stdout='root\n')
                with patch.object(installer,'ROOT',root), patch.object(installer,'DB',db), \
                     patch.object(installer,'UNIT',unit), patch.object(installer,'__file__',str(stage/'install.py')), \
                     patch.object(installer,'check_context'), patch.object(installer,'health'), \
                     patch.object(installer.socket,'gethostname',return_value='EDISUK'), \
                     patch.object(installer,'command',side_effect=command), \
                     patch.object(delivery,'transport',side_effect=self.rpc), \
                     patch.object(installer.subprocess,'run',return_value=subprocess.CompletedProcess([],0)), \
                     patch('builtins.open',side_effect=local_open):
                    if fail:
                        with self.assertRaises(subprocess.CalledProcessError):
                            installer.main()
                        self.assertEqual(target.read_bytes(),original)
                        self.assertFalse(unit.exists())
                        with sqlite3.connect(db) as con:
                            self.assertEqual(con.execute('SELECT enabled FROM vpn_personal_routing_delivery').fetchone()[0],0)
                    else:
                        installer.main()
                        self.assertTrue(unit.exists())
                        self.assertNotEqual(target.read_bytes(),original)
                    with sqlite3.connect(db) as con:
                        row=con.execute('SELECT revision,rules_json FROM vpn_personal_routing').fetchone()
                        self.assertEqual(row[0],2)
                        self.assertEqual(json.loads(row[1]),installer.NEW_RULES)

    def test_migration_refuses_changed_preference(self):
        with sqlite3.connect(self.db) as con:
            with self.assertRaises(RuntimeError):
                installer.check_source(con)
            con.execute('UPDATE vpn_personal_routing SET rules_json=?', (json.dumps(installer.OLD_RULES),))
            installer.check_source(con)
            con.execute('UPDATE vpn_personal_routing SET revision=2')
            with self.assertRaises(RuntimeError):
                installer.check_source(con)


# Run the existing endpoint authentication/CAS/isolation cases against the upgraded module.
import test_personal_api as existing
class UpgradedAPITests(existing.RoutingTests):
    def setUp(self):
        original = existing.routing
        existing.routing = api
        try:
            super().setUp()
        finally:
            existing.routing = original


if __name__ == '__main__':
    unittest.main()
