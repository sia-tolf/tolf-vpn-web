import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / 'setup/personal-routing/install-storage.py'
spec = importlib.util.spec_from_file_location('installer', SOURCE)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
MAIN = 'from fastapi import FastAPI\nimport tolf_promos\napp = FastAPI()\ndef authenticated_user_id(request):\n    return "example"\n'


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'tolf.db'
        with sqlite3.connect(self.db) as con:
            con.executescript('CREATE TABLE users(id TEXT PRIMARY KEY);'
                             'CREATE TABLE vpn_access(user_id TEXT, vpn_username TEXT);')
        (self.root / 'main.py').write_text(MAIN)
        for target, value in [('ROOT', self.root), ('DB', self.db)]:
            p = patch.object(installer, target, value)
            p.start()
            self.addCleanup(p.stop)
        for target, value in [('socket.gethostname', 'EDISUK'), ('os.geteuid', 0)]:
            owner, method = target.split('.')
            p = patch.object(getattr(installer, owner), method, return_value=value)
            p.start()
            self.addCleanup(p.stop)

    def test_success_preserves_existing_code(self):
        with patch.object(installer.subprocess, 'run'), patch.object(installer, 'wait_api'):
            installer.main()
        self.assertTrue((self.root / 'main.py').read_text().startswith(MAIN.rstrip()))
        self.assertTrue((self.root / installer.MODULE_NAME).exists())
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute('SELECT count(*) FROM vpn_personal_routing').fetchone()[0], 0)

    def test_failed_health_restores_code_not_database(self):
        with patch.object(installer.subprocess, 'run'), patch.object(installer, 'wait_api',
                side_effect=[None, RuntimeError('probe failed'), None]):
            with self.assertRaises(RuntimeError):
                installer.main()
        self.assertEqual((self.root / 'main.py').read_text(), MAIN)
        self.assertFalse((self.root / installer.MODULE_NAME).exists())
        with sqlite3.connect(self.db) as con:
            con.execute('SELECT count(*) FROM vpn_personal_routing')

    def test_existing_module_is_not_overwritten(self):
        target = self.root / installer.MODULE_NAME
        target.write_text('existing user code')
        with self.assertRaises(RuntimeError):
            installer.main()
        self.assertEqual(target.read_text(), 'existing user code')

    def test_wrong_host_is_rejected(self):
        with patch.object(installer.socket, 'gethostname', return_value='EDISLV'):
            with self.assertRaises(RuntimeError):
                installer.main()
        self.assertEqual((self.root / 'main.py').read_text(), MAIN)


if __name__ == '__main__':
    unittest.main()
