import importlib.util
import sqlite3
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

MODULE = Path(__file__).resolve().parents[2] / 'setup/personal-routing/tolf_personal_routing.py'
spec = importlib.util.spec_from_file_location('routing', MODULE)
routing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routing)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = str(Path(self.temp.name) / 'test.db')
        with sqlite3.connect(self.db) as con:
            con.executescript('''CREATE TABLE users(id TEXT PRIMARY KEY);
                CREATE TABLE vpn_access(user_id TEXT PRIMARY KEY,vpn_username TEXT);
                INSERT INTO users VALUES ('alice'),('bob');
                INSERT INTO vpn_access VALUES ('alice','vpn_alice'),('bob','vpn_bob');''')
        app = FastAPI()
        def auth(request):
            value = request.headers.get('x-test-user')
            if value not in ('alice', 'bob'):
                raise HTTPException(401, 'Not authenticated')
            return value
        routing.install(app, {'DB': self.db, 'ORIGIN': 'https://vpn.tolf.is',
            'authenticated_user_id': auth,
            'tolf_promos': SimpleNamespace(account_operation=lambda *args: nullcontext())})
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.headers = {'x-test-user': 'alice', 'origin': 'https://vpn.tolf.is'}

    def save(self, rules=None, revision=0, headers=None):
        return self.client.post('/vpn/routing-rules', headers=headers or self.headers,
            json={'revision': revision, 'routingRules': rules or {'riga': ['revolut.com']}})

    def test_storage_and_isolation(self):
        result = self.save()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['revision'], 1)
        self.assertEqual(result.json()['state'], 'pending')
        self.assertFalse(result.json()['enforcementAvailable'])
        self.assertIsNone(result.json()['appliedRevision'])
        self.assertIn('no-store', result.headers['cache-control'])
        bob = self.client.get('/vpn/routing-rules', headers={'x-test-user': 'bob'}).json()
        self.assertEqual(bob['revision'], 0)
        self.assertEqual(bob['routingRules']['riga'], [])

    def test_stale_save_rejected_and_identical_save_idempotent(self):
        self.save()
        self.assertEqual(self.save().status_code, 409)
        self.assertEqual(self.save(revision=1).json()['revision'], 1)

    def test_normalize_and_deduplicate(self):
        result = self.save({'riga': ['WISE.COM.', 'wise.com', 'münchen.de']}).json()
        self.assertEqual(result['routingRules']['riga'], ['wise.com', 'xn--mnchen-3ya.de'])

    def test_conflicts(self):
        for left, right in [('wise.com', 'wise.com'), ('wise.com', 'api.wise.com'),
                            ('api.wise.com', 'wise.com')]:
            self.assertEqual(self.save({'riga': [left], 'moscow': [right]}).status_code, 409)

    def test_invalid_domains(self):
        for value in ['127.0.0.1', 'https://wise.com', '*.wise.com', 'a;reboot.com',
                      '-bad.com', 'a..com', 'localhost', '', None, 5, 'xn--a.com', 'bad_name.com']:
            with self.subTest(value=value):
                self.assertEqual(self.save({'riga': [value]}).status_code, 400)

    def test_usa_unknown_exit_and_limits(self):
        for rules in [{'usa': ['example.com']}, {'uk': []}, {'riga': 'wise.com'},
                      {'riga': ['a.com'] * 201}]:
            self.assertEqual(self.save(rules).status_code, 400)

    def test_auth_origin_and_input_guards(self):
        self.assertEqual(self.client.get('/vpn/routing-rules').status_code, 401)
        self.assertEqual(self.client.post('/vpn/routing-rules', json={}).status_code, 401)
        self.assertEqual(self.save(headers={'x-test-user': 'alice', 'origin': 'https://evil.example'}).status_code, 403)
        self.assertEqual(self.save(headers={'x-test-user': 'alice'}).status_code, 403)
        self.assertEqual(self.save(revision=True).status_code, 400)
        self.assertEqual(self.client.post('/vpn/routing-rules', headers=self.headers, content='{}').status_code, 415)
        headers = {**self.headers, 'content-type': 'application/json'}
        self.assertEqual(self.client.post('/vpn/routing-rules', headers=headers, content='x').status_code, 400)
        self.assertEqual(self.client.post('/vpn/routing-rules', headers=headers, content='x'*65537).status_code, 413)

    def test_clear_rules(self):
        self.save()
        result = self.save({'riga': [], 'moscow': [], 'usa': []}, 1).json()
        self.assertEqual(result['revision'], 2)
        self.assertEqual(result['routingRules']['riga'], [])
        self.assertEqual(result['state'], 'pending')

    def test_deleted_vpn_cannot_save(self):
        with sqlite3.connect(self.db) as con:
            con.execute("DELETE FROM vpn_access WHERE user_id='alice'")
        self.assertEqual(self.save().status_code, 409)

    def test_cascade(self):
        self.save()
        with sqlite3.connect(self.db) as con:
            con.execute('PRAGMA foreign_keys=ON')
            con.execute("DELETE FROM users WHERE id='alice'")
            self.assertEqual(con.execute('SELECT count(*) FROM vpn_personal_routing').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
