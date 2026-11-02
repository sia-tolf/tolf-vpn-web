"""Install the optional country hint without modifying existing VPN endpoints."""
import argparse
import os
from pathlib import Path
import tempfile


REGISTRATION = '\n\n# TOLF Shadowrocket country hint\nimport tolf_client_country\ntolf_client_country.register(app)\n'


def atomic_write(path, data, mode=0o644):
    temporary = path.with_name(path.name + '.direct-country-new')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(fd, 'wb') as stream:
        os.fchmod(stream.fileno(), mode)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def install(target):
    main = target / 'main.py'
    helper = target / 'tolf_client_country.py'
    source = Path(__file__).with_name('client_country.py').read_bytes()
    before = main.read_text()
    after = before if 'tolf_client_country.register(app)' in before else before.rstrip() + REGISTRATION
    compile(source, str(helper), 'exec')
    compile(after, str(main), 'exec')
    backup = Path(tempfile.mkdtemp(prefix='shadowrocket-direct-country-backup-', dir=target.parent))
    (backup / 'main.py').write_bytes(main.read_bytes())
    if helper.exists():
        (backup / 'tolf_client_country.py').write_bytes(helper.read_bytes())
    atomic_write(helper, source)
    atomic_write(main, after.encode(), main.stat().st_mode & 0o777)
    print('Country hint installed; source backup:', backup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', type=Path, default=Path('/opt/tolf-api'))
    install(parser.parse_args().target)
