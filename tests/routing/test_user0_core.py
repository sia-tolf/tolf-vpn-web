import copy
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / 'setup/personal-routing/user0-service/core.py'
spec = importlib.util.spec_from_file_location('moscow_pilot', SOURCE)
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def event(user=b'user0', ike=b'11', vip=b'10.10.10.2', spi=b'ceebc121'):
    return {'ikev2-eap-domain': {
        'uniqueid': ike, 'state': b'ESTABLISHED', 'remote-id': b'rf',
        'remote-eap-id': user, 'remote-vips': [vip],
        'child-sas': {'child': {
            'state': b'INSTALLED', 'mode': b'TUNNEL', 'protocol': b'ESP',
            'reqid': b'244', 'spi-in': spi, 'remote-ts': [vip + b'/32']
        }}
    }}


class IdentityTests(unittest.TestCase):
    def test_moscow_override_uses_main_mark_and_lan_egress(self):
        rules = pilot.rule_batch(pilot.bindings([event()]))
        self.assertIn('meta mark set 0x100', rules)
        self.assertIn('meta mark 0x100 oifname "br-lan" counter', rules)
        self.assertNotIn('0x200', rules)

    def test_authenticated_identity_not_local_id(self):
        self.assertEqual(pilot.bindings([event()]), [('10.10.10.2', 244, 0xceebc121)])

    def test_remote_id_spoof_cannot_select_rules(self):
        e = event(b'other-user')
        e['ikev2-eap-domain']['remote-id'] = b'user0'
        self.assertEqual(pilot.bindings([e]), [])

    def test_missing_eap_id_does_not_fall_back(self):
        e = event()
        del e['ikev2-eap-domain']['remote-eap-id']
        e['ikev2-eap-domain']['remote-id'] = b'user0'
        self.assertEqual(pilot.bindings([e]), [])

    def test_shared_virtual_ip_fails_closed(self):
        with self.assertRaises(ValueError):
            pilot.bindings([event(), event(b'other', b'12')])

    def test_uninstalled_or_mismatched_child_cannot_select_rules(self):
        for changes in ({'state': b'INSTALLING'}, {'protocol': b'AH'},
                        {'remote-ts': [b'0.0.0.0/0']}):
            e = event()
            e['ikev2-eap-domain']['child-sas']['child'].update(changes)
            self.assertEqual(pilot.bindings([e]), [])

    def test_rekey_overlap_keeps_both_authenticated_spis(self):
        e = event()
        children = e['ikev2-eap-domain']['child-sas']
        children['old'] = copy.deepcopy(children['child'])
        children['old'].update(state=b'REKEYING', **{'spi-in': b'cf000001'})
        self.assertEqual(len(pilot.bindings([e])), 2)

    def test_disconnect_clears_all_routing_and_dns_chains(self):
        rules = pilot.rule_batch([])
        for name in ('guard', 'dns_redirect', 'mark_moscow', 'verify_exit'):
            self.assertIn('flush chain inet ' + pilot.TABLE + ' ' + name, rules)
        self.assertNotIn('dnat ip to', rules)
        self.assertNotIn('meta mark set', rules)
        self.assertIn('counter drop', rules)

    def test_reconnect_replaces_old_spi_without_old_ip_rule(self):
        new = pilot.bindings([event(vip=b'10.10.10.3', spi=b'cf000001')])
        rules = pilot.rule_batch(new)
        self.assertNotIn('10.10.10.2', rules)
        self.assertNotIn(str(0xceebc121), rules)
        self.assertIn('ip saddr 10.10.10.3 ipsec in reqid 244 ipsec in spi ' + str(0xcf000001), rules)

    def test_invalid_spi_cannot_enter_nft_program(self):
        with self.assertRaises(ValueError):
            pilot.bindings([event(spi=b'ffff; flush ruleset')])

    def test_unexpected_pool_fails_closed(self):
        with self.assertRaises(ValueError):
            pilot.bindings([event(vip=b'192.168.1.1')])

    def test_conntrack_cleanup_targets_only_redirected_port(self):
        with patch.object(pilot.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
            pilot.clean_connections(['10.10.10.2'])
        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            args = call.args[0]
            self.assertEqual(args[args.index('--reply-port-src') + 1], '1053')
            self.assertEqual(args[args.index('-s') + 1], '10.10.10.2')

    def test_conntrack_error_not_mistaken_for_empty_table(self):
        with patch.object(pilot.subprocess, 'run', return_value=subprocess.CompletedProcess(
                [], 1, stderr='Operation not permitted')):
            with self.assertRaises(RuntimeError):
                pilot.clean_connections(['10.10.10.2'])


if __name__ == '__main__':
    unittest.main()
