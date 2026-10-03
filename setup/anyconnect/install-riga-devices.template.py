"""Install Riga personal enforcement; UK activates this node separately."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

PAYLOAD = {}  # BUILD_RIGA_DEVICES
CONF = Path('/etc/ocserv/ocserv.conf')
DIRECTORY = Path('/etc/ocserv/tolf-uk')
PROFILES = Path('/etc/ocserv/tolf-device-config')
RUNTIME = Path('/run/tolf-oc-riga-devices')
ZONE = Path('/etc/tolf/openconnect/ru.zone')
SOCKET = '/run/occtl.socket'
CONTROLLER = Path('/usr/local/sbin/tolf-oc-riga-devices')
REMOTE = Path('/usr/local/sbin/tolf-oc-riga-remote')
HOOK = Path('/usr/local/sbin/tolf-oc-riga-device-hook')
SERVICE = Path('/etc/systemd/system/tolf-oc-riga-devices.service')
REFRESH = Path('/etc/systemd/system/tolf-oc-riga-devices-refresh.service')
TIMER = Path('/etc/systemd/system/tolf-oc-riga-devices-refresh.timer')


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True,
                          timeout=120).stdout


def options(source, name):
    return [match.group(1).strip('"') for line in source.splitlines()
            if (match := re.match(r'^\s*' + re.escape(name) + r'\s*=\s*(.*?)\s*$', line))]


def updated_config(source):
    expected = {'connect-script': str(HOOK), 'disconnect-script': str(HOOK),
                'config-per-user': str(PROFILES) + '/'}
    for name, value in expected.items():
        if options(source, name) not in ([], [value]):
            raise RuntimeError('Existing ' + name + ' needs integration')
    lines = [line for line in source.splitlines() if not re.match(
        r'^\s*(connect-script|disconnect-script|config-per-user)\s*=', line)]
    return '\n'.join(lines) + '\n' + '\n'.join(
        name + ' = ' + value for name, value in expected.items()) + '\n'


def atomic(path, data, mode=0o644):
    descriptor, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    stat = path.stat() if path.exists() else None
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            os.fchmod(stream.fileno(), stat.st_mode & 0o777 if stat else mode)
            if stat:
                os.fchown(stream.fileno(), stat.st_uid, stat.st_gid)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main():
    if os.geteuid() != 0:
        raise RuntimeError('Run as root on EDISLV')
    for tool in ('occtl', 'ocserv', 'openssl', 'nft', 'ip', 'dnstap-read', 'systemctl'):
        if not shutil.which(tool):
            raise RuntimeError('Missing tool: ' + tool)
    source = CONF.read_text()
    if options(source, 'ipv4-network') != ['10.19.0.0']:
        raise RuntimeError('Unexpected Riga VPN pool')
    if options(source, 'crl') != [str(DIRECTORY / 'uk-client-ca.crl.pem')]:
        raise RuntimeError('Install Riga UK CA/CRL foundation first')
    config = updated_config(source)
    connected = json.loads(run('occtl', '-s', SOCKET, '--json', 'show', 'users'))
    run('openssl', 'verify', '-CAfile', str(DIRECTORY / 'uk-client-ca.pem'),
        '-CRLfile', str(DIRECTORY / 'uk-client-ca.crl.pem'), '-crl_check',
        str(DIRECTORY / 'uk-client-ca.pem'))
    if not ZONE.is_file():
        raise RuntimeError('Riga RU zone not found')
    routes = [row for row in json.loads(run('ip', '-j', '-4', 'route', 'show', 'table', 'all'))
              if str(row.get('table')) == '118']
    if any(row.get('dst') != 'default' or row.get('dev') != 'gremoscow' for row in routes):
        raise RuntimeError('Route table 118 is already used')
    previous_rules = json.loads(run('ip', '-j', '-4', 'rule', 'show'))
    for row in previous_rules:
        if row.get('priority') in (1017, 1018):
            wanted = ('0x192', '118') if row['priority'] == 1017 else ('0x191', 'main')
            if (str(row.get('fwmark')), str(row.get('table'))) != wanted:
                raise RuntimeError('Riga personal rule priority conflict')
    backup = Path(tempfile.mkdtemp(prefix='devices-backup.', dir=CONF.parent))
    os.chmod(backup, 0o700)
    targets = [CONF, CONTROLLER, REMOTE, HOOK, SERVICE, REFRESH, TIMER]
    previous = {}
    for index, path in enumerate(targets):
        if path.is_symlink():
            raise RuntimeError('Unexpected symlink: ' + str(path))
        saved = backup / ('file-' + str(index))
        previous[path] = saved if path.exists() else None
        if path.exists():
            shutil.copy2(path, saved)
    nft = subprocess.run(['nft', 'list', 'table', 'inet', 'tolf_oc_riga_devices'],
                         capture_output=True, text=True)
    (backup / 'personal-table.nft').write_text(nft.stdout)
    states = {unit.name: {action: subprocess.run(
        ['systemctl', 'is-' + action, unit.name], capture_output=True).returncode == 0
        for action in ('enabled', 'active')} for unit in (SERVICE, TIMER)}
    DIRECTORY.joinpath('device-modes').mkdir(mode=0o700, exist_ok=True)
    PROFILES.mkdir(mode=0o755, exist_ok=True)
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    try:
        # Stop refresh jobs before replacing their executable or rule table.
        for unit in (TIMER, REFRESH, SERVICE):
            subprocess.run(['systemctl', 'stop', unit.name], capture_output=True)
        for name, path in (('riga-devices.py', CONTROLLER), ('riga-remote.py', REMOTE)):
            data = base64.b64decode(PAYLOAD[name]['data'])
            if hashlib.sha256(data).hexdigest() != PAYLOAD[name]['sha256']:
                raise RuntimeError('Embedded script hash mismatch')
            compile(data, name, 'exec')
            atomic(path, data, 0o755)
        atomic(HOOK, b'#!/bin/sh\nexec /usr/local/sbin/tolf-oc-riga-devices hook\n', 0o755)
        candidate = backup / 'config.new'
        candidate.write_text(config)
        run('ocserv', '-t', '-c', str(candidate))
        run(str(CONTROLLER), 'dns-refresh')
        atomic(CONF, config.encode())
        run('occtl', '-s', SOCKET, 'reload')
        # Sessions established before the hook was installed have no lease
        # binding. Reconnect only personal identities, preserving pilot users.
        def identities(value):
            if isinstance(value, str) and re.fullmatch(r'tolf-oc-[0-9a-f]{32}', value):
                yield value
            elif isinstance(value, dict):
                for item in value.values():
                    yield from identities(item)
            elif isinstance(value, list):
                for item in value:
                    yield from identities(item)
        for username in sorted(set(identities(connected))):
            run('occtl', '-s', SOCKET, 'disconnect', 'user', username)
        atomic(SERVICE, (
            '[Unit]\nDescription=TOLF Riga personal device enforcement\n'
            'After=network-online.target\nWants=network-online.target\nBefore=ocserv.service\n'
            '[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart=' + str(CONTROLLER) + ' apply\n'
            '[Install]\nWantedBy=multi-user.target\n').encode())
        atomic(REFRESH, (
            '[Unit]\nDescription=Refresh TOLF Riga device DNS routes\n'
            'After=tolf-oc-riga-devices.service\nRequires=tolf-oc-riga-devices.service\n'
            '[Service]\nType=oneshot\nExecStart=' + str(CONTROLLER) + ' dns-refresh\n').encode())
        atomic(TIMER, (
            '[Unit]\nDescription=Refresh TOLF Riga personal rules every minute\n'
            '[Timer]\nOnBootSec=30s\nOnUnitActiveSec=60s\n'
            '[Install]\nWantedBy=timers.target\n').encode())
        run('systemctl', 'daemon-reload')
        run('systemctl', 'enable', '--now', SERVICE.name, TIMER.name)
        run('systemctl', 'start', REFRESH.name)
        print(run(str(CONTROLLER), 'health').strip())
    except Exception:
        for unit in (TIMER, REFRESH, SERVICE):
            subprocess.run(['systemctl', 'stop', unit.name], capture_output=True)
            if unit.name in states and not states[unit.name]['enabled']:
                subprocess.run(['systemctl', 'disable', unit.name], capture_output=True)
        for path, saved in previous.items():
            if saved:
                shutil.copy2(saved, path)
            else:
                path.unlink(missing_ok=True)
        subprocess.run(['nft', 'delete', 'table', 'inet', 'tolf_oc_riga_devices'], capture_output=True)
        if nft.returncode == 0:
            subprocess.run(['nft', '-f', str(backup / 'personal-table.nft')], capture_output=True)
        for priority in (1017, 1018):
            if not any(row.get('priority') == priority for row in previous_rules):
                subprocess.run(['ip', '-4', 'rule', 'del', 'priority', str(priority)], capture_output=True)
        if not routes:
            subprocess.run(['ip', '-4', 'route', 'flush', 'table', '118'], capture_output=True)
        subprocess.run(['systemctl', 'daemon-reload'], capture_output=True)
        for unit in (SERVICE, TIMER):
            if states[unit.name]['active']:
                subprocess.run(['systemctl', 'start', unit.name], capture_output=True)
        subprocess.run(['occtl', '-s', SOCKET, 'reload'], capture_output=True)
        print('ERROR: previous configuration restored. Backup:', backup)
        raise
    print('OK: Riga personal device enforcement installed. Backup:', backup)
    print('UK registration/activation and the Riga website connection are next stages.')
    if not shutil.which('conntrack'):
        print('Mode changes will reconnect active devices until conntrack is installed.')


if __name__ == '__main__':
    main()
