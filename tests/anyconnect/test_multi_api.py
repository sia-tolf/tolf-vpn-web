import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
import uuid
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup/anyconnect'))
import tolf_anyconnect as api
from tolf_oc_certificates import initialize


class MultiApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.db = root / 'db'
        with sqlite3.connect(self.db) as con:
            con.execute('CREATE TABLE users(id TEXT PRIMARY KEY)')
            con.execute("INSERT INTO users VALUES ('owner')")
        fingerprint = initialize(root / 'anyconnect')
        (root / 'anyconnect/activation.json').write_text(json.dumps(
            dict(enabled=True, caSha256=fingerprint, nodes=['moscow', 'riga'])))
        self.modes = {'moscow': {}, 'riga': {}}
        self.fail = set()
        self.connected = set()
        self.calls = []
        def remote(name):
            def call(command):
                self.calls.append((name, command))
                action, *args = command.split()
                if (name, action) in self.fail:
                    raise ValueError('Unavailable')
                if action in ('tolf-oc-node-health', 'tolf-oc-crl-sync'):
                    return dict(status='ok', version=1, caSha256=fingerprint, deviceRouting=True)
                username = args[0]
                if action == 'tolf-oc-device':
                    self.modes[name][username] = args[1]
                    return dict(status='ok', username=username, mode=args[1])
                if action == 'tolf-oc-device-remove':
                    self.modes[name].pop(username, None)
                    return dict(status='ok', username=username, removed=True)
                return dict(status='ok', username=username, connected=name in self.connected)
            return call
        lock = threading.RLock()
        class Promos:
            @contextmanager
            def account_operation(self, db, user):
                with lock:
                    yield
        app = FastAPI()
        api.install(app, dict(DB=str(self.db), authenticated_user_id=lambda req: 'owner',
                             tolf_promos=Promos(), OC_REMOTES={name: remote(name) for name in self.modes}))
        self.client = TestClient(app)
        self.headers = {'Origin': 'https://vpn.tolf.is'}

    def tearDown(self):
        self.tmp.cleanup()

    def create(self):
        result = self.client.post('/oc/access/devices', headers=self.headers,
                                  json=dict(requestId=str(uuid.uuid4()), label='iPad'))
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()['device']

    def test_one_certificate_identity_and_two_connection_hosts(self):
        device = self.create()
        self.assertEqual(self.modes['riga'], self.modes['moscow'])
        token = self.client.post('/oc/access/devices/' + device['id'] + '/setup-link', headers=self.headers).json()['setupUrl'].split('#')[1]
        info = self.client.get('/oc/access/setup/' + token).json()
        self.assertEqual([c['host'] for c in info['connections']], ['oc.tolf.is:4443', 'oc-riga.tolf.is:443'])
        for connection, city in zip(info['connections'], ('Москва', 'Рига')):
            self.assertIn(device['username'], connection['connectionUri'])
            self.assertIn(city, connection['connectionName'])
            self.assertLessEqual(len(connection['connectionName']), 24)
        self.assertNotIn('password', info)
        self.assertEqual([c['connectionName'] for c in info['connections']], ['TOLF Москва iPad', 'TOLF Рига iPad'])

    def test_duplicate_device_titles_keep_readable_numbers_after_revocation(self):
        first = self.create()
        second = self.create()
        self.assertEqual(first['connectionNames']['moscow'], 'TOLF Москва iPad')
        self.assertEqual(second['connectionNames']['moscow'], 'TOLF Москва iPad 2')
        self.client.post('/oc/access/devices/' + first['id'] + '/revoke', headers=self.headers)
        listing = self.client.get('/oc/access/devices').json()['devices']
        self.assertEqual(next(d for d in listing if d['id'] == second['id'])['connectionNames'], second['connectionNames'])

    def test_truncated_labels_get_distinct_titles(self):
        rows = [dict(id=str(n), label='Long device label that exceeds the connection limit') for n in range(3)]
        titles = api.connection_titles(rows)
        for ingress in ('moscow', 'riga'):
            values = [titles[row['id']][ingress] for row in rows]
            self.assertEqual(len(set(values)), 3)
            self.assertTrue(all(len(title) <= 24 for title in values))

    def test_failed_policy_keeps_database_and_moscow_mode_and_pending_flag(self):
        device = self.create()
        self.fail.add(('riga', 'tolf-oc-device'))
        path = '/oc/access/devices/' + device['id'] + '/policy'
        self.assertEqual(self.client.post(path, headers=self.headers, json={'mode': 'ru'}).status_code, 503)
        self.assertEqual(self.modes['moscow'][device['username']], 'auto')
        policy = self.client.get(path).json()
        self.assertEqual(policy['mode'], 'auto')
        self.assertFalse(policy['applied'])
        self.fail.clear()
        self.assertEqual(self.client.post(path, headers=self.headers, json={'mode': 'lv'}).status_code, 200)
        self.assertTrue(self.client.get(path).json()['applied'])
        self.assertEqual(self.modes['riga'][device['username']], 'lv')

    def test_session_at_riga_and_partial_revocation(self):
        device = self.create()
        base = '/oc/access/devices/' + device['id']
        self.connected.add('riga')
        self.assertTrue(self.client.get(base + '/session').json()['connected'])
        self.fail.add(('moscow', 'tolf-oc-session'))
        response = self.client.get(base + '/session')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['complete'])
        self.connected.clear()
        self.assertEqual(self.client.get(base + '/session').status_code, 503)
        self.fail.add(('moscow', 'tolf-oc-device-remove'))
        self.assertEqual(self.client.post(base + '/revoke', headers=self.headers).status_code, 202)
        self.assertNotIn(device['username'], self.modes['riga'])
        self.fail.clear()
        self.assertEqual(self.client.post(base + '/revoke', headers=self.headers).status_code, 200)


if __name__ == '__main__':
    unittest.main()
