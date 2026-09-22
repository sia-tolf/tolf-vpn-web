"""Strict, dependency-free contract for the first account-scoped node receiver."""
import hashlib
import ipaddress
import json
from pathlib import Path
import re

ACCOUNT = '6e4f2559-fa36-410c-8b09-b299055d1ed6'
USERNAME = 'user0'
PROTOCOL = 2
MAX_BODY = 65536
EXITS = ('moscow', 'riga', 'usa')
POLICY_FILE = Path('/opt/tolf-user0-routing/policy.json')


def validate(value):
    if not isinstance(value, dict) or set(value) != {
            'protocol', 'accountId', 'vpnUsername', 'revision', 'routingRules'}:
        raise ValueError('Invalid policy fields')
    if type(value['protocol']) is not int or value['protocol'] != PROTOCOL:
        raise ValueError('Unsupported policy protocol')
    if value['accountId'] != ACCOUNT or value['vpnUsername'] != USERNAME:
        raise ValueError('This receiver is restricted to the enrolled account')
    revision = value['revision']
    if type(revision) is not int or not 0 <= revision < 2**53 - 1:
        raise ValueError('Invalid revision')
    groups = value['routingRules']
    if not isinstance(groups, dict) or set(groups) != set(EXITS):
        raise ValueError('Invalid exit groups')
    result = {}
    count = 0
    for exit_name in EXITS:
        domains = groups[exit_name]
        if not isinstance(domains, list):
            raise ValueError('Expected a domain list')
        count += len(domains)
        if count > 200 or (exit_name == 'usa' and domains):
            raise ValueError('Too many domains or unsupported USA exit')
        for domain in domains:
            if not isinstance(domain, str) or len(domain) > 253 or domain != domain.lower():
                raise ValueError('Expected canonical ASCII domain')
            labels = domain.split('.')
            if len(labels) < 2 or labels[-1].isdigit() or any(
                    not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', x)
                    for x in labels):
                raise ValueError('Invalid domain')
            for label in labels:
                if label.startswith('xn--'):
                    label.encode('ascii').decode('idna')
        result[exit_name] = sorted(set(domains))
    for first in result['moscow']:
        for second in result['riga']:
            if first == second or first.endswith('.' + second) or second.endswith('.' + first):
                raise ValueError('Overlapping domains cannot select different exits')
    return dict(value, routingRules=result)


def encoded(value):
    return json.dumps(validate(value), sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def load(path=None):
    raw = (path or POLICY_FILE).read_bytes()
    if len(raw) > MAX_BODY:
        raise ValueError('Policy too large')
    return validate(json.loads(raw))


def bootstrap():
    return {'protocol': PROTOCOL, 'accountId': ACCOUNT, 'vpnUsername': USERNAME,
            'revision': 0, 'routingRules': {'moscow': ['delfi.lv'], 'riga': [], 'usa': []}}


def nft_rules(current, table, dns, port, configured):
    lines = [f'flush chain inet {table} {chain}' for chain in
             ('guard', 'dns_redirect', 'mark_personal', 'verify_exit')]
    active = current if any(configured['routingRules'].values()) else []
    for vip, reqid, spi in active:
        ipaddress.IPv4Address(vip)
        reqid, spi = int(reqid), int(spi)
        match = f'ip saddr {vip} ipsec in reqid {reqid} ipsec in spi {spi}'
        lines += [
            f'add rule inet {table} guard ip daddr {dns} meta l4proto {{ tcp, udp }} '
            f'th dport {port} {match} ct status dnat counter accept',
            f'add rule inet {table} dns_redirect {match} ip daddr {dns} '
            f'meta l4proto {{ tcp, udp }} th dport 53 counter dnat ip to {dns}:{port}'
        ]
        for exit_name, other, mark, output in (
                ('moscow', 'riga', '0x100', '"br-lan"'),
                ('riga', 'moscow', '0x200', '{ "awgriga", "gre4-riga_gre" }')):
            if not configured['routingRules'][exit_name]:
                continue
            target = f'{match} ip daddr @{exit_name}4 ip daddr != @{other}4'
            lines += [
                f'add rule inet {table} mark_personal {target} counter meta mark set {mark}',
                f'add rule inet {table} verify_exit {target} meta mark {mark} '
                f'oifname {output} counter comment "{exit_name.upper()}"'
            ]
    lines += [
        f'add rule inet {table} guard iifname "lo" ip daddr {dns} '
        f'meta l4proto {{ tcp, udp }} th dport {port} accept',
        f'add rule inet {table} guard ip daddr {dns} '
        f'meta l4proto {{ tcp, udp }} th dport {port} counter drop'
    ]
    return '\n'.join(lines) + '\n'


def nft_addresses(data):
    result = set()
    for item in data['nftables']:
        for element in item.get('set', {}).get('elem', []):
            if isinstance(element, dict):
                element = element.get('elem', element)
                element = element['val']
            result.add(str(ipaddress.IPv4Address(element)))
    return result
