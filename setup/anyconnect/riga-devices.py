#!/usr/bin/python3
"""Riga data-plane device registry. No accounts, signing keys or certificates."""
from contextlib import contextmanager
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

DIRECTORY = Path('/etc/ocserv/tolf-uk')
RUNTIME = Path('/run/tolf-oc-riga-devices')
PROFILES = Path('/etc/ocserv/tolf-device-config')
CONF = Path('/etc/ocserv/ocserv.conf')
ZONE = Path('/etc/tolf/openconnect/ru.zone')
SOCKET = '/run/occtl.socket'
TABLE = 'tolf_oc_riga_devices'
MODES = {'auto', 'ru', 'lv', 'yt'}
POOL = ipaddress.ip_network('10.19.0.0/24')
YT_SUFFIXES = ('youtube.com', 'googlevideo.com', 'ytimg.com', 'youtu.be',
               'youtube-nocookie.com', 'youtubei.googleapis.com',
               'youtube.googleapis.com', 'yt3.ggpht.com')


def run(args, source=None, check=True, timeout=30):
    return subprocess.run(args, input=source, capture_output=True, text=True,
                          check=check, timeout=timeout)


def valid_cn(value):
    return bool(re.fullmatch(r'tolf-oc-[0-9a-f]{32}', value))


def valid_ip(value):
    try:
        address = ipaddress.ip_address(value)
        return address in POOL and 2 <= int(str(address).split('.')[-1]) <= 254
    except ValueError:
        return False


def write(path, text, mode=0o600):
    descriptor, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(text)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


@contextmanager
def locked():
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    descriptor = os.open(RUNTIME / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def mode_for(username):
    path = DIRECTORY / 'device-modes' / username
    if not path.exists():
        return 'deny'
    mode = path.read_text().strip()
    if mode not in MODES:
        raise RuntimeError('Invalid stored device mode')
    return mode


def bindings():
    result = []
    for path in sorted(RUNTIME.glob('tolf-oc-*')):
        username, separator, identifier = path.name.partition('.')
        if not valid_cn(username) or not separator or not re.fullmatch(r'[0-9]{1,20}', identifier):
            raise RuntimeError('Invalid runtime identity')
        address = path.read_text().strip()
        if not valid_ip(address):
            raise RuntimeError('Invalid runtime lease')
        result.append((username, identifier, address))
    return result


def rules(zone, leases, dns, now):
    """Build one atomic replacement, using own RU/YT sets and own marks."""
    networks = []
    for line in zone.splitlines():
        line = line.split('#', 1)[0].strip()
        if line:
            network = ipaddress.ip_network(line, strict=False)
            if network.version != 4:
                raise ValueError('RU zone must contain IPv4 networks')
            networks.append(str(network))
    if not networks:
        raise ValueError('RU zone is empty')
    lines = ['table inet ' + TABLE + ' {',
             'set ru4 { type ipv4_addr; flags interval; auto-merge; elements = { '
             + ', '.join(networks) + ' }; }']
    for kind in ('ru_domains4', 'yt_domains4'):
        addresses = sorted(str(ipaddress.IPv4Address(address))
                           for address, expiry in dns.get(kind, {}).items()
                           if float(expiry) > now)
        lines.append('set ' + kind + ' { type ipv4_addr;'
                     + (' elements = { ' + ', '.join(addresses) + ' };' if addresses else '') + ' }')
    for mode in ('ru', 'lv', 'auto', 'yt', 'deny'):
        addresses = sorted({address for _, _, address, value in leases if value == mode})
        if any(not valid_ip(address) for address in addresses):
            raise ValueError('Lease outside Riga pool')
        lines.append('set device_' + mode + ' { type ipv4_addr;'
                     + (' elements = { ' + ', '.join(addresses) + ' };' if addresses else '') + ' }')
    lines.extend(['chain route_devices { type filter hook prerouting priority -145; policy accept;',
                  'ip saddr @device_deny counter drop',
                  'ip saddr @device_ru meta mark set 0x192 counter'])
    for mode in ('lv', 'auto', 'yt'):
        lines.append('ip saddr @device_' + mode + ' meta mark set 0x191 counter')
    for mode in ('auto', 'yt'):
        for name in ('ru4', 'ru_domains4'):
            lines.append('ip saddr @device_' + mode + ' ip daddr @' + name
                         + ' meta mark set 0x192 counter')
    lines.append('ip saddr @device_yt ip daddr @yt_domains4 meta mark set 0x192 counter')
    lines.extend(['}', '}'])
    return '\n'.join(lines) + '\n'


def policy_rules(create=False):
    rows = json.loads(run(['ip', '-j', '-4', 'rule', 'show']).stdout)
    for priority, mark, table in ((1017, '0x192', '118'), (1018, '0x191', 'main')):
        matches = [row for row in rows if row.get('priority') == priority]
        if matches:
            if len(matches) != 1 or str(matches[0].get('fwmark')) != mark or str(matches[0].get('table')) != table:
                raise RuntimeError('Policy priority conflict: ' + str(priority))
        elif create:
            run(['ip', '-4', 'rule', 'add', 'priority', str(priority), 'fwmark', mark, 'lookup', table])
        else:
            raise RuntimeError('Personal policy rule missing: ' + str(priority))


def ensure_routes():
    policy_rules(create=True)
    run(['ip', '-4', 'route', 'replace', 'default', 'dev', 'gremoscow', 'table', '118'])


def apply():
    ensure_routes()
    cache = RUNTIME / 'dns.json'
    dns = json.loads(cache.read_text()) if cache.exists() else {}
    leases = [(user, identifier, address, mode_for(user)) for user, identifier, address in bindings()]
    source = rules(ZONE.read_text(), leases, dns, time.time())
    if run(['nft', 'list', 'table', 'inet', TABLE], check=False).returncode == 0:
        source = 'delete table inet ' + TABLE + '\n' + source
    run(['nft', '-f', '-'], source)


def disconnect(username):
    run(['occtl', '-s', SOCKET, 'disconnect', 'user', username], check=False)
    run(['occtl', '-s', SOCKET, '--json', 'show', 'users'])
    result = run(['occtl', '-s', SOCKET, '--json', 'show', 'user', username], check=False)
    if result.returncode != 2:
        raise RuntimeError('Device disconnect not acknowledged')


def clear_connections(username):
    if shutil.which('conntrack'):
        for user, _, address in bindings():
            if user == username:
                run(['conntrack', '-D', '-f', 'ipv4', '-s', address], check=False)
        return False
    return any(user == username for user, _, _ in bindings())


def dns_kind(name):
    name = name.rstrip('.').lower()
    if name.endswith(('.ru', '.su', '.xn--p1ai')):
        return 'ru_domains4'
    if any(name == suffix or name.endswith('.' + suffix) for suffix in YT_SUFFIXES):
        return 'yt_domains4'
    return None


def parse_dns(source, now, seen=None, observed=None):
    result = {'ru_domains4': {}, 'yt_domains4': {}}
    kind, answer, header = None, False, ''
    for line in source.splitlines():
        if ' CR ' in line:
            kind, answer = None, False
            header = line
            match = re.search(r' ([^ ]+)/IN/(?:A|HTTPS)$', line)
            if match and re.search(r'\b10\.19\.0\.(?:[0-9]{1,3})(?=[:#/\s])', line):
                kind = dns_kind(match.group(1))
            continue
        if line.startswith(';; ANSWER SECTION:'):
            answer = True
            continue
        if line.startswith(';; '):
            answer = False
        if kind and answer:
            match = re.match(r'^\S+\s+(\d+)\s+IN\s+A\s+(\S+)\s*$', line)
            if match:
                address = ipaddress.IPv4Address(match.group(2))
                if address.is_global:
                    # Identical historical records must not gain a fresh TTL
                    # whenever an active capture file receives unrelated data.
                    key = hashlib.sha256((header + '\n' + line).encode()).hexdigest()
                    expiry = (seen or {}).get(key, now + min(int(match.group(1)), 21600))
                    if observed is not None:
                        observed[key] = expiry
                    result[kind][str(address)] = max(expiry, result[kind].get(str(address), 0))
    return result


def refresh_dns():
    base = Path('/var/lib/tolf-openconnect')
    files = sorted(base.glob('dnstap-*.fstrm'), key=lambda p: p.stat().st_mtime, reverse=True)[:2]
    if not files and (base / 'dnstap.fstrm').exists():
        files = [base / 'dnstap.fstrm']
    collected = {'ru_domains4': {}, 'yt_domains4': {}}
    seen_path = RUNTIME / 'dns-seen.json'
    seen = json.loads(seen_path.read_text()) if seen_path.exists() else {}
    observed = {}
    for path in reversed(files):
        result = run(['dnstap-read', '-p', str(path)], timeout=45)
        parsed = parse_dns(result.stdout, min(time.time(), path.stat().st_mtime), seen, observed)
        for kind in collected:
            for address, expiry in parsed[kind].items():
                collected[kind][address] = max(expiry, collected[kind].get(address, 0))
    with locked():
        cache = RUNTIME / 'dns.json'
        previous = json.loads(cache.read_text()) if cache.exists() else {}
        for kind in collected:
            for address, expiry in previous.get(kind, {}).items():
                if expiry > time.time():
                    collected[kind][address] = max(expiry, collected[kind].get(address, 0))
            collected[kind] = {address: expiry for address, expiry in collected[kind].items()
                               if expiry > time.time()}
        write(cache, json.dumps(collected))
        write(seen_path, json.dumps(observed))
        apply()
        write(RUNTIME / 'last-dns-refresh', str(time.time()))


def hook():
    username = os.environ.get('USERNAME', '')
    identifier = os.environ.get('ID', '')
    address = os.environ.get('IP_REMOTE', '')
    if not re.fullmatch(r'[0-9]{1,20}', identifier) or not valid_ip(address):
        raise ValueError('Invalid hook lease')
    personal = username.startswith('tolf-oc-')
    if personal and not valid_cn(username):
        raise ValueError('Invalid hook identity')
    with locked():
        reason = os.environ.get('REASON')
        if reason == 'connect':
            # IP reuse by either a legacy or personal client removes stale bindings.
            for user, session_id, ip in bindings():
                if ip == address:
                    (RUNTIME / (user + '.' + session_id)).unlink()
            if personal:
                write(RUNTIME / (username + '.' + identifier), address)
            try:
                apply()
                if personal and mode_for(username) == 'deny':
                    raise RuntimeError('Device is not registered')
            except Exception:
                # A deny lease stays in place for an unregistered personal CN.
                raise
        elif reason == 'disconnect':
            path = RUNTIME / (username + '.' + identifier)
            if personal and path.exists() and path.read_text().strip() == address:
                path.unlink()
            apply()
        else:
            raise ValueError('Unsupported hook reason')


def health():
    expected = (DIRECTORY / 'uk-client-ca.sha256').read_text().strip()
    ca = DIRECTORY / 'uk-client-ca.pem'
    der = subprocess.run(['openssl', 'x509', '-in', str(ca), '-outform', 'DER'],
                         check=True, capture_output=True, timeout=10).stdout
    if hashlib.sha256(der).hexdigest() != expected:
        raise RuntimeError('CA fingerprint mismatch')
    run(['openssl', 'verify', '-CAfile', str(ca), '-CRLfile',
         str(DIRECTORY / 'uk-client-ca.crl.pem'), '-crl_check', str(ca)])
    config = CONF.read_text()
    for line in ('connect-script = /usr/local/sbin/tolf-oc-riga-device-hook',
                 'disconnect-script = /usr/local/sbin/tolf-oc-riga-device-hook',
                 'config-per-user = ' + str(PROFILES) + '/'):
        if line not in config.splitlines():
            raise RuntimeError('Device hook configuration missing')
    run(['occtl', '-s', SOCKET, '--json', 'show', 'users'])
    for name in ('device_deny', 'ru4', 'ru_domains4', 'yt_domains4'):
        run(['nft', 'list', 'set', 'inet', TABLE, name])
    refreshed = float((RUNTIME / 'last-dns-refresh').read_text())
    if time.time() - refreshed > 180:
        raise RuntimeError('DNS refresh is stale')
    routes = run(['ip', '-4', 'route', 'show', 'table', '118']).stdout
    if 'default dev gremoscow' not in routes:
        raise RuntimeError('Moscow route missing')
    policy_rules()
    return {'status': 'ok', 'version': 1, 'caSha256': expected,
            'deviceRouting': True, 'issuance': False}


def main(argv):
    operation = argv[0] if argv else ''
    if operation == 'hook' and len(argv) == 1:
        hook()
        return None
    if operation == 'apply' and len(argv) == 1:
        with locked():
            apply()
        return None
    if operation == 'dns-refresh' and len(argv) == 1:
        refresh_dns()
        return None
    if operation == 'health' and len(argv) == 1:
        return health()
    if len(argv) < 2 or not valid_cn(argv[1]):
        raise ValueError('Invalid operation or identity')
    username = argv[1]
    if operation == 'session' and len(argv) == 2:
        run(['occtl', '-s', SOCKET, '--json', 'show', 'users'])
        result = run(['occtl', '-s', SOCKET, '--json', 'show', 'user', username], check=False)
        if result.returncode not in (0, 2):
            raise RuntimeError('Session unavailable')
        return {'status': 'ok', 'username': username, 'connected': result.returncode == 0}
    if operation == 'set' and len(argv) == 3 and argv[2] in MODES:
        mode = argv[2]
        with locked():
            path = DIRECTORY / 'device-modes' / username
            old = mode_for(username)
            write(path, mode + '\n')
            try:
                apply()
                write(PROFILES / username, 'max-same-clients = 1\n', 0o644)
            except Exception:
                if old == 'deny':
                    path.unlink(missing_ok=True)
                else:
                    write(path, old + '\n')
                apply()
                raise
            reconnect = clear_connections(username) if old != mode else False
        if reconnect:
            disconnect(username)
        return {'status': 'ok', 'username': username, 'mode': mode}
    if operation == 'remove' and len(argv) == 2:
        with locked():
            (DIRECTORY / 'device-modes' / username).unlink(missing_ok=True)
            (PROFILES / username).unlink(missing_ok=True)
            apply()
            clear_connections(username)
        disconnect(username)
        return {'status': 'ok', 'username': username, 'removed': True}
    raise ValueError('Unsupported device operation')


if __name__ == '__main__':
    try:
        reply = main(sys.argv[1:])
        if reply is not None:
            print(json.dumps(reply, separators=(',', ':')))
    except Exception as error:
        print(json.dumps({'status': 'error', 'error': str(error)}))
        sys.exit(1)
