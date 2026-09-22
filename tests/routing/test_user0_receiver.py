import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2] / 'setup/personal-routing/user0-service'
sys.path.insert(0, str(ROOT))
try:
    spec = importlib.util.spec_from_file_location('user0_rpc', ROOT / 'rpc.py')
    rpc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rpc)
finally:
    sys.path.pop(0)
policy = rpc.policy


class ContractTests(unittest.TestCase):
    def test_only_enrolled_account_can_set_rules(self):
        for key, value in [('accountId', 'other'), ('vpnUsername', 'user_other'), ('revision', True)]:
            data = policy.bootstrap()
            data[key] = value
            with self.assertRaises(ValueError):
                policy.validate(data)

    def test_domains_cannot_inject_dnsmasq_or_nft(self):
        for domain in ['delfi.lv\nuser=nobody', 'a.lv/#inet#fw4#ru4', '*.delfi.lv', '1.2.3.4',
                       'xn--.lv', 'https://delfi.lv', 'delfi.lv;flush ruleset']:
            data = policy.bootstrap()
            data['routingRules']['moscow'] = [domain]
            with self.assertRaises((ValueError, UnicodeError)):
                policy.validate(data)

    def test_conflicting_parent_domain_is_rejected(self):
        data = policy.bootstrap()
        data['routingRules']['riga'] = ['www.delfi.lv']
        with self.assertRaises(ValueError):
            policy.validate(data)

    def test_duplicate_order_is_canonical(self):
        first = policy.bootstrap()
        first['routingRules']['moscow'] = ['b.lv', 'a.lv', 'a.lv']
        second = copy.deepcopy(first)
        second['routingRules']['moscow'] = ['a.lv', 'b.lv']
        self.assertEqual(policy.digest(first), policy.digest(second))

    def test_empty_policy_withdraws_redirect_and_mark_rules(self):
        data = policy.bootstrap()
        data['routingRules']['moscow'] = []
        rules = policy.nft_rules([('10.10.10.2', 1, 256)], 'test', '10.254.0.53', 1053, data)
        self.assertNotIn('dnat ip to', rules)
        self.assertNotIn('meta mark set', rules)
        self.assertIn('counter drop', rules)

    def test_shared_addresses_are_excluded_from_both_exit_overrides(self):
        data = policy.bootstrap()
        data['routingRules']['riga'] = ['example.lv']
        rules = policy.nft_rules([('10.10.10.2', 1, 256)], 'test', '10.254.0.53', 1053, data)
        self.assertIn('ip daddr @moscow4 ip daddr != @riga4', rules)
        self.assertIn('ip daddr @riga4 ip daddr != @moscow4', rules)

    def test_set_parser_accepts_timed_elements(self):
        value = {'nftables': [{'set': {'elem': ['104.20.18.136',
                    {'elem': {'val': '172.66.161.144', 'timeout': 86400, 'expires': 80000}}]}}]}
        self.assertEqual(policy.nft_addresses(value), {'104.20.18.136', '172.66.161.144'})


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for owner, name, value in [(rpc, 'ROOT', self.root), (rpc, 'STATUS', self.root/'status.json'),
                                   (policy, 'POLICY_FILE', self.root/'policy.json')]:
            mock = patch.object(owner, name, value)
            mock.start()
            self.addCleanup(mock.stop)
        policy.POLICY_FILE.write_bytes(policy.encoded(policy.bootstrap()))

    def test_acceptance_is_not_application(self):
        data = policy.bootstrap()
        data['revision'] = 1
        report = rpc.accept(data)
        self.assertEqual(report['acceptedRevision'], 1)
        self.assertIsNone(report['appliedRevision'])
        self.assertEqual(report['state'], 'pending')

    def test_stale_and_same_revision_changes_are_rejected(self):
        data = policy.bootstrap()
        data['revision'] = 2
        rpc.accept(data)
        with self.assertRaisesRegex(ValueError, 'Stale'):
            rpc.accept(policy.bootstrap())
        data['routingRules']['moscow'] = ['example.lv']
        with self.assertRaisesRegex(ValueError, 'different'):
            rpc.accept(data)
        self.assertEqual(policy.load()['routingRules']['moscow'], ['delfi.lv'])

    def test_identical_retry_does_not_rewrite_or_restart(self):
        data = policy.bootstrap()
        with patch.object(rpc, 'write_policy') as write:
            rpc.accept(data)
            write.assert_not_called()

    def write_status(self, **changes):
        data = policy.bootstrap()
        status = dict(pid=123, updated=time.time(), protocol=2, policyRevision=0,
                      policyDigest=policy.digest(data), bindings=[['10.10.10.2', 1, 256]],
                      conflictingAddresses=0)
        status.update(changes)
        rpc.STATUS.write_text(json.dumps(status))

    def get_report(self):
        original = Path.read_bytes
        def read(path):
            if str(path).startswith('/proc/'):
                return b'python3\0' + str(self.root/'service.py').encode() + b'\0'
            return original(path)
        with patch.object(Path, 'read_bytes', read):
            return rpc.report()

    def test_matching_fresh_runtime_acknowledges_applied_revision(self):
        self.write_status()
        report = self.get_report()
        self.assertEqual(report['state'], 'applied')
        self.assertEqual(report['appliedRevision'], 0)

    def test_missing_session_is_ready_not_active(self):
        self.write_status(bindings=[])
        self.assertEqual(self.get_report()['state'], 'ready')

    def test_stale_runtime_and_wrong_digest_cannot_acknowledge(self):
        for changes in ({'updated': time.time()-60}, {'policyDigest': 'wrong'}, {'protocol': 1}):
            self.write_status(**changes)
            self.assertIsNone(self.get_report()['appliedRevision'])

    def test_shared_ip_conflict_is_not_acknowledged_as_applied(self):
        self.write_status(conflictingAddresses=1)
        report = self.get_report()
        self.assertEqual(report['state'], 'conflict')
        self.assertIsNone(report['appliedRevision'])


if __name__ == '__main__':
    unittest.main()
