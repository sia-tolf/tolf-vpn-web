"""Durable, single-account routing delivery; no VPN provisioning or profile edits."""
import fcntl
import json
import logging
import os
from pathlib import Path
import sqlite3
import subprocess
import time
from contextlib import closing

import tolf_routing_contract as contract
import tolf_nodes

DB = '/var/lib/tolf-api/tolf.db'
SSH = ['/usr/bin/ssh', '-T', '-i', '/opt/tolf-api/provision_ed25519',
       '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
       '-o', 'UserKnownHostsFile=/opt/tolf-api/.ssh/known_hosts',
       '-o', 'ConnectTimeout=10', 'tolfprov@' + tolf_nodes.RIGA_PUBLIC_HOST]
FRESH = 60
EMPTY = {'moscow': [], 'riga': [], 'usa': []}


def connect(db):
    con = sqlite3.connect(db, timeout=15)
    con.row_factory = sqlite3.Row
    return con


def initialize(db):
    with closing(connect(db)) as con, con:
        # Intentionally survives deletion of the source account, to deliver withdrawal.
        con.execute('''CREATE TABLE IF NOT EXISTS vpn_personal_routing_delivery (
            account_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 0,
            intent_json TEXT, source_revision INTEGER, node_revision INTEGER NOT NULL DEFAULT 0,
            observed_json TEXT, observed_at REAL, last_error TEXT
        )''')


def source(con):
    row = con.execute('''SELECT p.revision,p.rules_json,p.vpn_username
        FROM vpn_personal_routing p JOIN users u ON u.id=p.user_id
        JOIN vpn_access v ON v.user_id=u.id
        WHERE u.id=? AND v.vpn_username=? AND p.vpn_username=v.vpn_username''',
        (contract.ACCOUNT, contract.USERNAME)).fetchone()
    owners = con.execute('SELECT COUNT(*) FROM vpn_access WHERE vpn_username=?',
                         (contract.USERNAME,)).fetchone()[0]
    if row is None or owners != 1:
        return None, EMPTY
    return row['revision'], json.loads(row['rules_json'])


def make_intent(revision, rules):
    return contract.validate(dict(protocol=2, accountId=contract.ACCOUNT,
                                  vpnUsername=contract.USERNAME, revision=revision, routingRules=rules))


def enqueue(db):
    with closing(connect(db)) as con, con:
        con.execute('BEGIN IMMEDIATE')
        row = con.execute('SELECT * FROM vpn_personal_routing_delivery WHERE account_id=?',
                          (contract.ACCOUNT,)).fetchone()
        if row is None or not row['enabled']:
            return None
        revision, rules = source(con)
        previous = json.loads(row['intent_json']) if row['intent_json'] else None
        canonical = make_intent(0, rules)['routingRules']
        if (previous is None or row['source_revision'] != revision
                or previous['routingRules'] != canonical):
            node_revision = max(row['node_revision'] + 1, revision or 0)
            intent = make_intent(node_revision, canonical)
            con.execute('''UPDATE vpn_personal_routing_delivery SET intent_json=?,
                source_revision=?,node_revision=?,observed_json=NULL,observed_at=NULL,last_error=NULL
                WHERE account_id=?''', (contract.encoded(intent).decode(), revision,
                                       node_revision, contract.ACCOUNT))
        else:
            intent = previous
        return intent


def transport(action, intent=None):
    if action not in ('status', 'apply'):
        raise ValueError('Unsupported delivery action')
    body = contract.encoded(intent) if action == 'apply' else b''
    result = subprocess.run(SSH + ['personal-routing-user0 ' + action], input=body,
                            capture_output=True, timeout=40, check=False)
    if result.returncode or len(result.stdout) > 65536:
        raise RuntimeError('Receiver unavailable or rejected revision')
    value = json.loads(result.stdout)
    if (not isinstance(value, dict) or value.get('protocol') != 2 or value.get('status') != 'ok'
            or value.get('accountId') != contract.ACCOUNT or value.get('vpnUsername') != contract.USERNAME
            or value.get('node') != 'moscow' or value.get('scope') != 'moscow-ikev2-eap-domain'):
        raise ValueError('Unexpected receiver response')
    return value


def validate_report(value, intent):
    if (type(value.get('acceptedRevision')) is not int or value['acceptedRevision'] != intent['revision']
            or value.get('acceptedDigest') != contract.digest(intent)
            or value.get('state') not in ('pending', 'applied', 'ready', 'conflict')):
        raise ValueError('Receiver acknowledged a different revision')
    if value['state'] in ('applied', 'ready'):
        if (type(value.get('appliedRevision')) is not int or value['appliedRevision'] != intent['revision']
                or value.get('appliedDigest') != contract.digest(intent)):
            raise ValueError('Receiver application acknowledgement does not match')


def record(db, intent, report=None):
    with closing(connect(db)) as con, con:
        con.execute('BEGIN IMMEDIATE')
        # An old RPC response cannot acknowledge a newer intent or changed account.
        revision, rules = source(con)
        row = con.execute('SELECT * FROM vpn_personal_routing_delivery WHERE account_id=?',
                          (contract.ACCOUNT,)).fetchone()
        if (row is None or not row['enabled'] or row['intent_json'] != contract.encoded(intent).decode()
                or row['source_revision'] != revision or intent['routingRules'] != make_intent(0, rules)['routingRules']):
            return
        con.execute('''UPDATE vpn_personal_routing_delivery
            SET observed_json=?,observed_at=?,last_error=? WHERE account_id=?''',
            (json.dumps(report) if report is not None else None, time.time(),
             None if report is not None else 'node_unavailable', contract.ACCOUNT))


def cycle(db, rpc=transport):
    intent = enqueue(db)
    if intent is None:
        return
    try:
        report = rpc('status')
        if report.get('acceptedRevision') != intent['revision'] or report.get('acceptedDigest') != contract.digest(intent):
            # A node revision ahead of this database requires review; do not overwrite it.
            if type(report.get('acceptedRevision')) is not int or report['acceptedRevision'] >= intent['revision']:
                raise ValueError('Receiver revision conflict')
            report = rpc('apply', intent)
        validate_report(report, intent)
        record(db, intent, report)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        record(db, intent)
        logging.warning('Personal routing: node delivery unavailable; saved policy retained')


def enrich(con, user_id, username, snapshot):
    if user_id != contract.ACCOUNT or username != contract.USERNAME:
        return snapshot
    try:
        row = con.execute('SELECT * FROM vpn_personal_routing_delivery WHERE account_id=?', (user_id,)).fetchone()
    except sqlite3.OperationalError:
        return snapshot
    if row is None or not row['enabled']:
        return snapshot
    snapshot.update(enforcementAvailable=True, scope='moscow-ikev2-eap-domain', state='pending',
                    appliedRevision=None, deliveryError=None)
    if (row['source_revision'] != snapshot['revision'] or not row['intent_json']
            or json.loads(row['intent_json'])['routingRules'] != snapshot['routingRules']):
        return snapshot
    if row['observed_at'] is None:
        return snapshot
    if not 0 <= time.time() - row['observed_at'] < FRESH or row['last_error']:
        snapshot.update(state='unavailable', deliveryError='node_unavailable')
        return snapshot
    try:
        report = json.loads(row['observed_json'])
        validate_report(report, json.loads(row['intent_json']))
    except (ValueError, KeyError, TypeError):
        snapshot.update(state='unavailable', deliveryError='invalid_acknowledgement')
        return snapshot
    snapshot['state'] = report['state']
    if report['state'] in ('applied', 'ready'):
        snapshot['appliedRevision'] = snapshot['revision']
    return snapshot


def main():
    # One worker across service restarts/manual invocations; no dependency on a browser.
    with open(str(Path(DB).parent / 'personal-routing-delivery.lock'), 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            try:
                cycle(DB)
            except Exception:
                logging.exception('Personal routing reconciliation failed')
            time.sleep(10)


if __name__ == '__main__':
    main()
