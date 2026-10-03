from pathlib import Path
import sys
import unittest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup/anyconnect'))
from tolf_oc_nodes import Nodes


class Stub:
    def __init__(self, failures=(), connected=False):
        self.calls = []
        self.failures = set(failures)
        self.connected = connected

    def action(self, name, *args):
        self.calls.append((name, *args))
        if name in self.failures:
            raise HTTPException(503, 'Unavailable')

    def set(self, username, mode):
        self.action('set', username, mode)

    def remove(self, username):
        self.action('remove', username)

    def sync_crl(self):
        self.action('crl')

    def session(self, username):
        self.action('session', username)
        return self.connected

    def health(self, fresh=False):
        self.calls.append(('health', fresh))
        return 'health' not in self.failures


class NodesTests(unittest.TestCase):
    def test_one_identity_is_registered_at_both_nodes(self):
        moscow, riga = Stub(), Stub()
        Nodes({'moscow': moscow, 'riga': riga}).set('device', 'auto')
        self.assertEqual(moscow.calls, [('set', 'device', 'auto')])
        self.assertEqual(riga.calls, moscow.calls)

    def test_partial_creation_removes_even_unknown_failed_registration(self):
        moscow, riga = Stub(), Stub(('set',))
        with self.assertRaises(HTTPException):
            Nodes({'moscow': moscow, 'riga': riga}).set('device', 'auto')
        self.assertIn(('remove', 'device'), moscow.calls)
        self.assertIn(('remove', 'device'), riga.calls)

    def test_failed_policy_restores_previous_mode_at_both_nodes(self):
        moscow, riga = Stub(), Stub(('set',))
        with self.assertRaises(HTTPException) as error:
            Nodes({'moscow': moscow, 'riga': riga}).set('device', 'ru', 'lv')
        self.assertIn(('set', 'device', 'lv'), moscow.calls)
        self.assertIn(('set', 'device', 'lv'), riga.calls)
        self.assertEqual(error.exception.detail, 'Ingress synchronization pending')

    def test_revocation_reaches_riga_when_moscow_is_down(self):
        moscow, riga = Stub(('crl', 'remove')), Stub()
        with self.assertRaises(HTTPException):
            Nodes({'moscow': moscow, 'riga': riga}).revoke('device')
        self.assertEqual(riga.calls, [('crl',), ('remove', 'device')])

    def test_disconnect_still_attempted_when_crl_refresh_fails(self):
        node = Stub(('crl',))
        with self.assertRaises(HTTPException):
            Nodes({'moscow': node}).revoke('device')
        self.assertIn(('remove', 'device'), node.calls)

    def test_riga_session_and_unknown_moscow_are_distinguished(self):
        result = Nodes({'moscow': Stub(('session',)),
                        'riga': Stub(connected=True)}).sessions('device')
        self.assertTrue(result['connected'])
        self.assertFalse(result['complete'])
        self.assertIsNone(result['nodes']['moscow']['connected'])
        self.assertTrue(result['nodes']['riga']['connected'])

    def test_all_nodes_health_checked_even_when_first_is_down(self):
        moscow, riga = Stub(('health',)), Stub()
        self.assertFalse(Nodes({'moscow': moscow, 'riga': riga}).health(fresh=True))
        self.assertEqual(riga.calls, [('health', True)])


if __name__ == '__main__':
    unittest.main()
