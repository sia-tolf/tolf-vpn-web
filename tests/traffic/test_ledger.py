from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup/traffic'))
from tolf_traffic import Ledger

START = '2026-10-01T00:00:00Z'
END = '2026-11-01T00:00:00Z'


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'db'
        with sqlite3.connect(self.db) as con:
            con.executescript('''CREATE TABLE users(id TEXT); INSERT INTO users VALUES ('a'),('b'),('c');
            CREATE TABLE vpn_access(user_id TEXT,vpn_username TEXT);
            INSERT INTO vpn_access VALUES ('a','alice'),('b','bob');
            CREATE TABLE oc_devices(user_id TEXT,id TEXT,label TEXT,username TEXT);
            INSERT INTO oc_devices VALUES ('a','tablet','iPad','tolf-oc-device');''')
        self.ledger = Ledger(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def event(self, eid='start', kind='start', up=0, down=0, second=0, username='alice', protocol='ikev2', session='boot-1/session-1'):
        return dict(eventId=eid,kind=kind,upload=up,download=down,observedAt=f'2026-10-03T10:00:{second:02d}Z',username=username,protocol=protocol,sessionId=session)

    def totals(self):
        return self.ledger.summary(START, END)['totals']

    def test_duplicates_and_final_bytes_are_counted_once(self):
        self.ledger.ingest('moscow', [self.event(), self.event('interim','interim',100,200,10), self.event('stop','stop',150,250,20)])
        self.assertEqual(self.ledger.ingest('moscow',[self.event('stop','stop',150,250,20)]), ['duplicate'])
        self.assertEqual(self.totals()['total'], 400)
        self.assertEqual(self.totals()['upload'], 150)
        self.assertEqual(self.totals()['download'], 250)

    def test_existing_connection_baseline_does_not_backfill_history(self):
        self.ledger.ingest('riga', [self.event('baseline','baseline',1000,2000), self.event('i','interim',1030,2040,10)])
        self.assertEqual(self.totals()['total'], 70)

    def test_reordered_snapshot_and_duplicate_content_conflict(self):
        self.ledger.ingest('riga',[self.event(), self.event('new','interim',100,200,20)])
        self.assertEqual(self.ledger.ingest('riga',[self.event('old','interim',30,50,10)]), ['stale'])
        with self.assertRaises(ValueError):
            self.ledger.ingest('riga',[self.event('new','interim',101,200,20)])
        self.assertEqual(self.totals()['total'], 300)

    def test_counter_reset_is_rejected_and_reconnect_has_new_id(self):
        self.ledger.ingest('riga',[self.event(),self.event('i','interim',100,100,10)])
        with self.assertRaises(ValueError):
            self.ledger.ingest('riga',[self.event('reset','interim',5,5,20)])
        self.ledger.ingest('riga',[self.event('s2',session='boot-2/session-1'),self.event('i2','interim',5,5,20,session='boot-2/session-1')])
        self.assertEqual(self.totals()['total'], 210)

    def test_nodes_and_protocols_do_not_collide(self):
        for node in ('moscow','riga'):
            self.ledger.ingest(node,[self.event(),self.event('i','interim',10,20,10)])
            self.ledger.ingest(node,[self.event('oc-start',username='tolf-oc-device',protocol='anyconnect'),self.event('oc-i','interim',30,40,10,username='tolf-oc-device',protocol='anyconnect')])
        summary = self.ledger.summary(START,END,'a')
        self.assertEqual(summary['totals']['total'], 200)
        self.assertEqual(len(summary['breakdown']),4)
        self.assertEqual(next(r for r in summary['breakdown'] if r['protocol']=='anyconnect')['deviceLabel'],'iPad')

    def test_ambiguous_or_unknown_attribution_is_separate(self):
        with sqlite3.connect(self.db) as con:
            con.execute("INSERT INTO vpn_access VALUES ('b','alice')")
        self.ledger.ingest('riga',[self.event(),self.event('i','interim',10,20,10)])
        self.assertEqual(self.ledger.summary(START,END)['unmatched'],dict(upload=10,download=20))
        self.assertEqual(self.ledger.summary(START,END,'a')['totals']['total'],0)

    def test_attribution_survives_account_mapping_changes(self):
        self.ledger.ingest('riga',[self.event()])
        with sqlite3.connect(self.db) as con:
            con.execute("UPDATE vpn_access SET user_id='b' WHERE vpn_username='alice'")
        self.ledger.ingest('riga',[self.event('i','interim',10,20,10)])
        self.assertEqual(self.ledger.summary(START,END,'a')['totals']['total'],30)
        self.assertEqual(self.ledger.summary(START,END,'b')['totals']['total'],0)

    def test_sorting_is_global_before_pagination_and_includes_zero_users(self):
        for username,size in [('alice',10),('bob',100)]:
            self.ledger.ingest('riga',[self.event(username,username=username,session=username),self.event(username+'i','interim',size,size,10,username=username,session=username)])
        self.assertEqual([r['accountId'] for r in self.ledger.ranked_accounts(START,END)],['b','a','c'])
        self.assertEqual(self.ledger.ranked_accounts(START,END,offset=1,limit=1)[0]['accountId'],'a')
        self.assertEqual(self.ledger.ranked_accounts(START,END,descending=False)[0]['accountId'],'c')
        for sort in ('upload','download','lastActivity'):
            self.assertEqual(len(self.ledger.ranked_accounts(START,END,sort=sort)),3)
        with self.assertRaises(ValueError):
            self.ledger.ranked_accounts(START,END,sort='total; DROP TABLE users')

    def test_restart_retains_receipts_and_counters(self):
        self.ledger.ingest('moscow',[self.event(),self.event('i','interim',1,2,10)])
        self.ledger = Ledger(self.db)
        self.assertEqual(self.ledger.ingest('moscow',[self.event('i','interim',1,2,10)]), ['duplicate'])
        self.assertEqual(self.totals()['total'],3)

    def test_batch_failure_rolls_back_every_event(self):
        invalid = self.event('invalid','interim',1,1,20,session='unknown')
        with self.assertRaises(ValueError):
            self.ledger.ingest('moscow',[self.event(),invalid])
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute('SELECT count(*) FROM traffic_streams').fetchone()[0],0)

    def test_period_boundaries_and_timezone(self):
        self.ledger.ingest('moscow',[self.event(),self.event('i','interim',1,2,10)])
        self.assertEqual(self.ledger.summary('2026-10-03T15:00:10+05:00','2026-10-03T15:00:11+05:00')['totals']['total'],3)
        self.assertEqual(self.ledger.summary('2026-10-03T10:00:00Z','2026-10-03T10:00:10Z')['totals']['total'],0)

    def test_boolean_negative_naive_timestamp_and_untrusted_node_rejected(self):
        for key,value in [('upload',True),('download',-1),('observedAt','2026-10-03T10:00:00'),('username','')]:
            event=self.event();event[key]=value
            with self.assertRaises(ValueError):self.ledger.ingest('riga',[event])
        with self.assertRaises(ValueError):self.ledger.ingest('internet',[self.event()])


if __name__ == '__main__':
    unittest.main()
