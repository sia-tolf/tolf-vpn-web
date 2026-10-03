from pathlib import Path
import os
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'setup/anyconnect/moscow-riga-transit.sh'


class RigaTransitTests(unittest.TestCase):
    def execute(self, rule):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tool = root / 'ip'
            tool.write_text('#!/bin/sh\nif [ "$3" = show ]; then printf "%s\\n" "$TOLF_RULE"; '
                            'else printf "%s\\n" "$*" >> "$TOLF_CALLS"; fi\n')
            tool.chmod(0o755)
            calls = root / 'calls'
            env = dict(os.environ, PATH=tmp + ':' + os.environ['PATH'],
                       TOLF_RULE=rule, TOLF_CALLS=str(calls))
            result = subprocess.run(['sh', str(SCRIPT)], env=env, capture_output=True, text=True)
            return result.returncode, calls.read_text() if calls.exists() else ''

    def test_adds_only_narrow_transit_rule(self):
        code, calls = self.execute('10005: from 10.19.0.0/24 lookup 100')
        self.assertEqual(code, 0)
        self.assertEqual(calls.strip(), '-4 rule add priority 8983 from 10.19.0.0/24 iif gre4-riga_gre lookup main')

    def test_existing_correct_rule_is_idempotent(self):
        code, calls = self.execute('8983: from 10.19.0.0/24 iif gre4-riga_gre lookup main')
        self.assertEqual(code, 0)
        self.assertEqual(calls, '')

    def test_conflicting_priority_is_never_changed(self):
        code, calls = self.execute('8983: from all lookup 100')
        self.assertNotEqual(code, 0)
        self.assertEqual(calls, '')


if __name__ == '__main__':
    unittest.main()
