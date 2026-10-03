"""UK traffic ledger. Called by trusted collectors, never by a browser endpoint.

Counters are VPN payload bytes: upload is received by the ingress, download is
sent by the ingress. A stream must survive rekeys and have a fresh ID on restart.
"""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import sqlite3


MAX_COUNTER = 2**63 - 1
SCHEMA = """
CREATE TABLE IF NOT EXISTS traffic_streams (
    node TEXT NOT NULL, protocol TEXT NOT NULL, session_id TEXT NOT NULL,
    username TEXT NOT NULL, account_id TEXT, device_id TEXT, device_label TEXT,
    upload INTEGER NOT NULL, download INTEGER NOT NULL,
    observed_at TEXT NOT NULL, closed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(node,protocol,session_id)
);
CREATE TABLE IF NOT EXISTS traffic_receipts (
    node TEXT NOT NULL, event_id TEXT NOT NULL, digest TEXT NOT NULL,
    PRIMARY KEY(node,event_id)
);
CREATE TABLE IF NOT EXISTS traffic_deltas (
    node TEXT NOT NULL, event_id TEXT NOT NULL, protocol TEXT NOT NULL,
    session_id TEXT NOT NULL, account_id TEXT, device_id TEXT, device_label TEXT,
    observed_at TEXT NOT NULL, upload INTEGER NOT NULL, download INTEGER NOT NULL,
    PRIMARY KEY(node,event_id)
);
CREATE INDEX IF NOT EXISTS traffic_period ON traffic_deltas(observed_at,account_id);
CREATE INDEX IF NOT EXISTS traffic_account_period ON traffic_deltas(account_id,observed_at);
"""


def stamp(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be text')
    instant = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if instant.utcoffset() is None:
        raise ValueError('Timestamp needs a timezone')
    return instant.astimezone(timezone.utc).isoformat(timespec='microseconds')


def period(start, end):
    start, end = stamp(start), stamp(end)
    span = datetime.fromisoformat(end) - datetime.fromisoformat(start)
    if not 0 < span.total_seconds() <= 366 * 86400:
        raise ValueError('Period must be positive and no more than 366 days')
    return start, end


def text(value, limit):
    if not isinstance(value, str) or not value or len(value) > limit or any(ord(c) < 32 for c in value):
        raise ValueError('Invalid identifier')
    return value


def resolve(con, protocol, username):
    """Freeze unambiguous account attribution when the stream is first seen."""
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    matches = set()
    if protocol == 'anyconnect' and 'oc_devices' in tables:
        for row in con.execute('SELECT user_id,id,label FROM oc_devices WHERE username=?', (username,)):
            matches.add((row[0], row[1], row[2]))
    if protocol == 'ikev2':
        if 'vpn_access' in tables:
            matches.update((r[0], None, None) for r in con.execute('SELECT user_id FROM vpn_access WHERE vpn_username=?', (username,)))
        if 'managed_users' in tables:
            matches.update((r[0], None, None) for r in con.execute('SELECT account_id FROM managed_users WHERE vpn_username=?', (username,)) if r[0])
        if 'windows_devices' in tables:
            matches.update((r[0], r[1], r[2]) for r in con.execute('SELECT user_id,id,name FROM windows_devices WHERE username=?', (username,)))
    accounts = {m[0] for m in matches}
    if len(accounts) != 1:
        return None, None, None
    account = accounts.pop()
    devices = {m for m in matches if m[1] is not None}
    return devices.pop() if len(devices) == 1 else (account, None, None)


class Ledger:
    def __init__(self, database):
        self.database = str(database)
        with closing(self.connect()) as con, con:
            con.executescript(SCHEMA)

    def connect(self):
        con = sqlite3.connect(self.database, timeout=30)
        con.row_factory = sqlite3.Row
        return con

    def ingest(self, source_node, events):
        if source_node not in ('moscow', 'riga') or not isinstance(events, list) or len(events) > 1000:
            raise ValueError('Invalid batch')
        results = []
        with closing(self.connect()) as con, con:
            con.execute('BEGIN IMMEDIATE')
            for raw in events:
                if not isinstance(raw, dict) or set(raw) != {'eventId','protocol','sessionId','username','observedAt','upload','download','kind'}:
                    raise ValueError('Invalid event fields')
                event = dict(raw)
                event['eventId'] = text(event['eventId'], 128)
                event['sessionId'] = text(event['sessionId'], 256)
                event['username'] = text(event['username'], 256)
                event['observedAt'] = stamp(event['observedAt'])
                if event['protocol'] not in ('ikev2', 'anyconnect') or event['kind'] not in ('start','baseline','interim','stop'):
                    raise ValueError('Invalid event type')
                for key in ('upload', 'download'):
                    if type(event[key]) is not int or not 0 <= event[key] <= MAX_COUNTER:
                        raise ValueError('Invalid byte counter')
                if event['kind'] == 'start' and (event['upload'] or event['download']):
                    raise ValueError('Start must have zero counters')
                digest = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()
                prior = con.execute('SELECT digest FROM traffic_receipts WHERE node=? AND event_id=?', (source_node, event['eventId'])).fetchone()
                if prior:
                    if prior['digest'] != digest:
                        raise ValueError('Event ID reused with different content')
                    results.append('duplicate')
                    continue
                identity = (source_node, event['protocol'], event['sessionId'])
                stream = con.execute('SELECT * FROM traffic_streams WHERE node=? AND protocol=? AND session_id=?', identity).fetchone()
                delta_upload = delta_download = 0
                if stream is None:
                    if event['kind'] not in ('start', 'baseline'):
                        raise ValueError('Missing initial baseline')
                    account, device, label = resolve(con, event['protocol'], event['username'])
                    con.execute('INSERT INTO traffic_streams VALUES (?,?,?,?,?,?,?,?,?,?,0)',
                                identity + (event['username'], account, device, label, event['upload'], event['download'], event['observedAt']))
                    status = 'baseline'
                else:
                    if stream['username'] != event['username']:
                        raise ValueError('Stream identity changed')
                    account, device, label = stream['account_id'], stream['device_id'], stream['device_label']
                    if event['observedAt'] < stream['observed_at']:
                        status = 'stale'
                    elif stream['closed']:
                        if (event['upload'], event['download']) != (stream['upload'], stream['download']):
                            raise ValueError('Closed stream counters changed')
                        status = 'closed'
                    else:
                        if event['kind'] in ('start', 'baseline'):
                            raise ValueError('Baseline repeated for existing stream')
                        delta_upload = event['upload'] - stream['upload']
                        delta_download = event['download'] - stream['download']
                        if min(delta_upload, delta_download) < 0:
                            raise ValueError('Counter reset requires a new stream ID')
                        con.execute('UPDATE traffic_streams SET upload=?,download=?,observed_at=?,closed=? WHERE node=? AND protocol=? AND session_id=?',
                                    (event['upload'], event['download'], event['observedAt'], int(event['kind'] == 'stop')) + identity)
                        status = 'counted'
                con.execute('INSERT INTO traffic_receipts VALUES (?,?,?)', (source_node, event['eventId'], digest))
                if delta_upload or delta_download:
                    con.execute('INSERT INTO traffic_deltas VALUES (?,?,?,?,?,?,?,?,?,?)',
                                (source_node, event['eventId'], event['protocol'], event['sessionId'], account, device, label, event['observedAt'], delta_upload, delta_download))
                results.append(status)
        return results

    def summary(self, start, end, account_id=None):
        start, end = period(start, end)
        where = 'observed_at>=? AND observed_at<?'
        args = [start, end]
        if account_id is not None:
            where += ' AND account_id=?'
            args.append(account_id)
        with closing(self.connect()) as con:
            total = dict(con.execute('SELECT COALESCE(sum(upload),0) AS upload,COALESCE(sum(download),0) AS download,max(observed_at) AS lastActivity FROM traffic_deltas WHERE ' + where, args).fetchone())
            breakdown = [dict(r) for r in con.execute('SELECT node,protocol,device_id AS deviceId,device_label AS deviceLabel,sum(upload) AS upload,sum(download) AS download FROM traffic_deltas WHERE ' + where + ' GROUP BY node,protocol,device_id,device_label ORDER BY node,protocol,device_id', args)]
            days = [dict(r) for r in con.execute('SELECT substr(observed_at,1,10) AS day,sum(upload) AS upload,sum(download) AS download FROM traffic_deltas WHERE ' + where + ' GROUP BY day ORDER BY day', args)]
            unmatched = dict(con.execute('SELECT COALESCE(sum(upload),0) AS upload,COALESCE(sum(download),0) AS download FROM traffic_deltas WHERE observed_at>=? AND observed_at<? AND account_id IS NULL', (start, end)).fetchone()) if account_id is None else None
        total['total'] = total['upload'] + total['download']
        return {'start': start, 'end': end, 'totals': total, 'breakdown': breakdown, 'daysUtc': days, 'unmatched': unmatched}

    def ranked_accounts(self, start, end, sort='total', descending=True, offset=0, limit=50):
        start, end = period(start, end)
        if sort not in ('total','upload','download','lastActivity') or type(descending) is not bool or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('Invalid sorting or pagination')
        direction = 'DESC' if descending else 'ASC'
        with closing(self.connect()) as con:
            rows = con.execute('''SELECT u.id AS accountId,COALESCE(t.upload,0) AS upload,
                COALESCE(t.download,0) AS download,COALESCE(t.upload,0)+COALESCE(t.download,0) AS total,t.lastActivity
                FROM users u LEFT JOIN (SELECT account_id,sum(upload) AS upload,sum(download) AS download,max(observed_at) AS lastActivity
                FROM traffic_deltas WHERE observed_at>=? AND observed_at<? GROUP BY account_id) t ON t.account_id=u.id
                ORDER BY ''' + sort + ' ' + direction + ',u.id ASC LIMIT ? OFFSET ?', (start, end, limit, offset)).fetchall()
        return [dict(row) for row in rows]
