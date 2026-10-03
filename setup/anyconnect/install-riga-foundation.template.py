"""Install public UK trust/CRL on the existing Debian Riga ocserv instance."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

SYNC = ""  # BUILD_RIGA_SYNC
DIRECTORY = Path('/etc/ocserv/tolf-uk')
CONF = Path('/etc/ocserv/ocserv.conf')
SOCKET = '/run/occtl.socket'
SERVICE = Path('/etc/systemd/system/tolf-oc-riga-crl-sync.service')
TIMER = Path('/etc/systemd/system/tolf-oc-riga-crl-sync.timer')
SYNC_PATH = Path('/usr/local/sbin/tolf-oc-riga-crl-sync')


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True,
                          timeout=60).stdout


def options(source, name):
    values = []
    for line in source.splitlines():
        match = re.match(r'^\s*' + re.escape(name) + r'\s*=\s*(.*?)\s*$', line)
        if match:
            values.append(match.group(1).strip('"'))
    return values


def updated_config(source):
    if 'certificate' not in options(source, 'auth') + options(source, 'enable-auth'):
        raise RuntimeError('Certificate authentication must already be enabled')
    if len(options(source, 'ca-cert')) != 1:
        raise RuntimeError('Expected exactly one ca-cert setting')
    crl = str(DIRECTORY / 'uk-client-ca.crl.pem')
    if options(source, 'crl') not in ([], [crl]):
        raise RuntimeError('Existing CRL needs integration')
    lines = [line for line in source.splitlines()
             if not re.match(r'^\s*crl\s*=', line)]
    return '\n'.join(lines) + '\ncrl = ' + crl + '\n'


def atomic(path, content, mode=0o644):
    path = Path(path)
    stat = path.stat() if path.exists() else None
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            os.fchmod(stream.fileno(), stat.st_mode & 0o777 if stat else mode)
            if stat:
                os.fchown(stream.fileno(), stat.st_uid, stat.st_gid)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def fingerprint(path):
    data = subprocess.run(['openssl', 'x509', '-in', str(path), '-outform', 'DER'],
                          check=True, capture_output=True, timeout=20).stdout
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('ca_sha256')
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{64}', args.ca_sha256):
        raise RuntimeError('Expected SHA256 fingerprint')
    if os.geteuid() != 0:
        raise RuntimeError('Run as root on EDISLV')
    for tool in ('openssl', 'curl', 'occtl', 'ocserv', 'systemctl', 'sha256sum', 'cmp'):
        if not shutil.which(tool):
            raise RuntimeError('Missing tool: ' + tool)
    source = CONF.read_text()
    config = updated_config(source)
    trust = Path(options(source, 'ca-cert')[0])
    if not trust.is_absolute() or not trust.is_file() or trust.is_symlink():
        raise RuntimeError('Expected a regular absolute CA file')
    run('occtl', '-s', SOCKET, '--json', 'show', 'users')
    backup = Path(tempfile.mkdtemp(prefix='uk-foundation-backup.', dir=CONF.parent))
    os.chmod(backup, 0o700)
    ca = backup / 'download-ca.pem'
    crl = backup / 'download-crl.pem'
    for endpoint, destination, limit in (('ca.pem', ca, '65536'), ('crl.pem', crl, '1048576')):
        run('curl', '-fsS', '--connect-timeout', '10', '--max-time', '30',
            '--max-filesize', limit, 'https://api.tolf.is/oc/access/' + endpoint,
            '-o', str(destination))
    if fingerprint(ca) != args.ca_sha256:
        raise RuntimeError('UK CA fingerprint mismatch')
    run('openssl', 'verify', '-CAfile', str(ca), '-CRLfile', str(crl),
        '-crl_check', str(ca))
    # Exact DER identity, not merely a certificate accepted by the trust bundle.
    present = False
    for number, block in enumerate(re.findall(
            rb'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----',
            trust.read_bytes(), re.S)):
        cert = backup / ('existing-' + str(number) + '.pem')
        cert.write_bytes(block + b'\n')
        if fingerprint(cert) == args.ca_sha256:
            present = True
    combined = trust.read_bytes()
    if not present:
        combined = combined.rstrip() + b'\n' + ca.read_bytes()
    DIRECTORY.mkdir(mode=0o755, exist_ok=True)
    files = [CONF, trust, DIRECTORY / 'uk-client-ca.pem',
             DIRECTORY / 'uk-client-ca.sha256', DIRECTORY / 'uk-client-ca.crl.pem',
             SYNC_PATH, SERVICE, TIMER]
    previous = {}
    for number, path in enumerate(files):
        if path.is_symlink():
            raise RuntimeError('Unexpected symlink: ' + str(path))
        saved = backup / ('file-' + str(number))
        previous[path] = saved if path.exists() else None
        if path.exists():
            shutil.copy2(path, saved)
    (backup / 'restore-map.txt').write_text('\n'.join(
        str(path) + ' <- ' + (str(saved) if saved else 'absent')
        for path, saved in previous.items()))
    timer_enabled = subprocess.run(['systemctl', 'is-enabled', TIMER.name],
                                   capture_output=True).returncode == 0
    timer_active = subprocess.run(['systemctl', 'is-active', TIMER.name],
                                  capture_output=True).returncode == 0
    try:
        atomic(DIRECTORY / 'uk-client-ca.pem', ca.read_bytes())
        atomic(DIRECTORY / 'uk-client-ca.sha256', (args.ca_sha256 + '\n').encode())
        atomic(trust, combined)
        atomic(SYNC_PATH, SYNC.encode(), 0o755)
        run('sh', '-n', str(SYNC_PATH))
        # Existing CRL numbers are checked by the same sync logic as Moscow.
        run(str(SYNC_PATH))
        candidate = backup / 'config.new'
        candidate.write_text(config)
        run('ocserv', '-t', '-c', str(candidate))
        atomic(CONF, config.encode())
        run('occtl', '-s', SOCKET, 'reload')
        atomic(SERVICE, (
            '[Unit]\nDescription=TOLF Riga signed UK CRL synchronization\n'
            'After=network-online.target ocserv.service\n'
            '[Service]\nType=oneshot\nExecStart=' + str(SYNC_PATH) + '\n').encode())
        atomic(TIMER, (
            '[Unit]\nDescription=Refresh TOLF Riga CRL every five minutes\n'
            '[Timer]\nOnBootSec=1min\nOnUnitActiveSec=5min\n'
            '[Install]\nWantedBy=timers.target\n').encode())
        run('systemctl', 'daemon-reload')
        run('systemctl', 'enable', '--now', TIMER.name)
        run('systemctl', 'start', SERVICE.name)
        run('occtl', '-s', SOCKET, '--json', 'show', 'users')
    except Exception:
        subprocess.run(['systemctl', 'stop', TIMER.name], capture_output=True)
        if not timer_enabled:
            subprocess.run(['systemctl', 'disable', TIMER.name], capture_output=True)
        for path, saved in previous.items():
            if saved:
                shutil.copy2(saved, path)
            else:
                path.unlink(missing_ok=True)
        subprocess.run(['systemctl', 'daemon-reload'], capture_output=True)
        if timer_active:
            subprocess.run(['systemctl', 'start', TIMER.name], capture_output=True)
        subprocess.run(['occtl', '-s', SOCKET, 'reload'], capture_output=True)
        print('ERROR: previous files restored. Backup:', backup)
        raise
    print('OK: Riga trusts UK device CA; signed CRL synchronization enabled.')
    print('CA SHA256:', args.ca_sha256)
    print('Backup:', backup)
    print('Personal device registration/routing: next stage, not installed yet.')
    print(run('openssl', 'crl', '-in', str(DIRECTORY / 'uk-client-ca.crl.pem'),
              '-noout', '-issuer', '-lastupdate', '-nextupdate', '-crlnumber'))


if __name__ == '__main__':
    main()
