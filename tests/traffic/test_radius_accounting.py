import hashlib
import importlib.util
from pathlib import Path
import struct
import socket
import subprocess
import sqlite3
import os
import runpy
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location('radius_accounting',
    Path(__file__).resolve().parents[2] / 'setup/traffic/radius_accounting.py')
radius = importlib.util.module_from_spec(spec)
spec.loader.exec_module(radius)
SECRET = b'a-local-random-secret-of-at-least-32-bytes'


def request(status=1, upload=0, download=0, identifier=3, delay=0, extra=b'', timestamp=1791040000, elapsed=60):
    def attr(kind, value):
        value = struct.pack('!I', value) if isinstance(value, int) else value
        return bytes((kind, len(value) + 2)) + value
    attrs = (attr(1, b'user0') + attr(44, b'daemon-17') + attr(40, status) +
             (attr(55, timestamp) if timestamp is not None else b'') + attr(41, delay) +
             attr(46, elapsed) +
             attr(42, upload & 0xffffffff) + attr(52, upload >> 32) +
             attr(43, download & 0xffffffff) + attr(53, download >> 32) + extra)
    header = struct.pack('!BBH', 4, identifier, 20 + len(attrs))
    return header + hashlib.md5(header + bytes(16) + attrs + SECRET).digest() + attrs


class AccountingTests(unittest.TestCase):
    def test_gigawords_and_direction(self):
        event, _ = radius.decode(request(2, 2**32 + 7, 2**33 + 9), SECRET)
        self.assertEqual((event['upload'], event['download']), (2**32 + 7, 2**33 + 9))
        self.assertEqual(event['kind'], 'stop')

    def test_retry_identity_and_response_authenticator(self):
        a, _ = radius.decode(request(3, 17, 30), SECRET)
        packet = request(3, 17, 30, identifier=99, delay=15)
        b, response = radius.decode(packet, SECRET)
        self.assertEqual(a, b)
        self.assertEqual(response[:4], struct.pack('!BBH', 5, 99, 20))
        self.assertEqual(response[4:20], hashlib.md5(response[:4] + packet[4:20] + SECRET).digest())

    def test_native_strongswan_packet_without_event_timestamp(self):
        packet = request(3, 17, 30, timestamp=None)
        event, _ = radius.decode(packet, SECRET, received_at=1791040000)
        retry, _ = radius.decode(request(3, 17, 30, timestamp=None, delay=5),
                                 SECRET, received_at=1791040006)
        self.assertEqual(event['eventId'], retry['eventId'])
        self.assertNotEqual(event['observedAt'], retry['observedAt'])
        spool = radius.Spool(':memory:')
        spool.record(event)
        spool.record(retry)
        self.assertEqual(spool.pending(), [event])
        spool.close()

    def test_zero_traffic_interims_remain_distinct_by_session_time(self):
        one, _ = radius.decode(request(3, timestamp=None, elapsed=60), SECRET)
        two, _ = radius.decode(request(3, timestamp=None, elapsed=120), SECRET)
        self.assertNotEqual(one['eventId'], two['eventId'])

    def test_conflicting_retry_payload_is_rejected(self):
        event, _ = radius.decode(request(timestamp=None), SECRET)
        spool = radius.Spool(':memory:')
        spool.record(event)
        with self.assertRaises(ValueError):
            spool.record(dict(event, username='different-user'))
        spool.close()

    def test_wrong_secret_and_corruption_rejected(self):
        for packet, secret in ((request(), b'x' * 32), (request()[:-1], SECRET),
                               (request() + b'garbage', SECRET)):
            with self.assertRaises(ValueError):
                radius.decode(packet, secret)

    def test_duplicate_and_malformed_attributes_rejected(self):
        for extra in (bytes((40, 6)) + struct.pack('!I', 1), b'\x03\x01', b'\x03'):
            with self.assertRaises(ValueError):
                radius.decode(request(extra=extra), SECRET)

    def test_nonzero_start_and_counter_overflow_rejected(self):
        for packet in (request(1, 1), request(2, 2**63)):
            with self.assertRaises(ValueError):
                radius.decode(packet, SECRET)

    def test_proxy_state_echoed(self):
        extra = b'\x21\x05one\x21\x05two'
        packet = request(extra=extra)
        _, response = radius.decode(packet, SECRET)
        self.assertEqual(response[20:], extra)
        self.assertEqual(response[4:20], hashlib.md5(response[:4] + packet[4:20] + extra + SECRET).digest())

    def test_spool_survives_restart_deduplicates_and_acknowledges(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'spool.db'
            spool = radius.Spool(path)
            spool.receive(request(), SECRET)
            spool.receive(request(identifier=8, delay=5), SECRET)
            spool.receive(request(2, 90, 200), SECRET)
            spool.close()
            spool = radius.Spool(path)
            self.assertEqual([e['kind'] for e in spool.pending()], ['start', 'stop'])
            first = spool.pending()[0]['eventId']
            spool.acknowledge([first])
            spool.acknowledge([first])
            self.assertEqual(len(spool.pending()), 1)
            spool.close()

    def test_storage_failure_prevents_acknowledgement(self):
        spool = radius.Spool(':memory:')
        with patch.object(spool, 'record', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                spool.receive(request(), SECRET)
        self.assertEqual(spool.pending(), [])
        spool.close()

    def test_loopback_service_persists_before_real_udp_reply(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            key = base / 'secret'
            key.write_bytes(SECRET)
            os.chmod(key, 0o600)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            import sys
            process = subprocess.Popen([sys.executable, spec.origin,
                '--database', str(base / 'spool.db'), '--secret-file', str(key),
                '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                packet = request(2, 800, 1500, timestamp=None)
                event, expected = radius.decode(packet, SECRET)
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.settimeout(0.2)
                    response = None
                    for _ in range(25):
                        sock.sendto(packet, ('127.0.0.1', port))
                        try:
                            response, peer = sock.recvfrom(4096)
                            break
                        except socket.timeout:
                            if process.poll() is not None:
                                self.fail(process.stderr.read().decode())
                    self.assertEqual(response, expected)
                with sqlite3.connect(base / 'spool.db') as con:
                    self.assertEqual(con.execute('SELECT event_id FROM events').fetchall(),
                                     [(event['eventId'],)])
                self.assertEqual((base / 'spool.db').stat().st_mode & 0o077, 0)
            finally:
                process.terminate()
                process.communicate(timeout=5)

    def test_wrong_server_guard_precedes_any_mutation(self):
        path = Path(__file__).resolve().parents[2] / 'setup/traffic/install-moscow-receiver-template.py'
        installer = runpy.run_path(str(path))
        fake = subprocess.CompletedProcess([], 1, stdout='', stderr='no br-lan')
        with patch('os.geteuid', return_value=0), patch('shutil.which', return_value='/sbin/ip'), \
             patch('subprocess.run', return_value=fake), \
             patch('tempfile.mkdtemp', side_effect=AssertionError('mutation before guard')):
            with self.assertRaisesRegex(SystemExit, 'only for Moscow OpenWrt'):
                installer['main']()


if __name__ == '__main__':
    unittest.main()
