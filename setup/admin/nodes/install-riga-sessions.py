#!/usr/bin/python3
"""Install read-only session inventory behind the existing provisioning gate."""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time

PAYLOAD = 'IyEvdXNyL2Jpbi9weXRob24zCiIiIlJlYWQtb25seSBub2RlIGludmVudG9yeS4gTmV2ZXIgdXNlIHJhdy1vdXRwdXQgcGFyc2luZyB0byBhdXRob3JpemUgbXV0YXRpb25zLiIiIgppbXBvcnQganNvbgppbXBvcnQgb3MKaW1wb3J0IHJlCmltcG9ydCBzdWJwcm9jZXNzCmltcG9ydCBzeXMKZnJvbSBkYXRldGltZSBpbXBvcnQgZGF0ZXRpbWUsIHRpbWV6b25lCgpWRVJTSU9OID0gJzEuMC4wJwpTU0ggPSBbJy91c3IvYmluL3NzaCcsICctbicsICctaScsICcvcm9vdC8uc3NoL2lkX2VkMjU1MTlfaWtlX3VzZXJzX3N5bmMnLAogICAgICAgJy1vJywgJ0lkZW50aXRpZXNPbmx5PXllcycsICctbycsICdCYXRjaE1vZGU9eWVzJywgJy1vJywgJ1N0cmljdEhvc3RLZXlDaGVja2luZz15ZXMnLAogICAgICAgJy1vJywgJ0Nvbm5lY3RUaW1lb3V0PTEwJywgJ3Jvb3RAMTAuMzEuMC4xJ10KCgpkZWYgcGFyc2VfbWVzc2FnZSh0ZXh0KToKICAgIG1hdGNoZXMgPSBsaXN0KHJlLmZpbmRpdGVyKHInW15cc3t9PVxbXF1dK3xbe309XFtcXV0nLCB0ZXh0KSkKICAgIHRva2VucyA9IFttYXRjaC5ncm91cCgpIGZvciBtYXRjaCBpbiBtYXRjaGVzXQogICAgaW5kZXggPSAwCgogICAgZGVmIHRha2UoKToKICAgICAgICBub25sb2NhbCBpbmRleAogICAgICAgIGlmIGluZGV4ID49IGxlbih0b2tlbnMpOgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdUcnVuY2F0ZWQgaW52ZW50b3J5JykKICAgICAgICB2YWx1ZSA9IHRva2Vuc1tpbmRleF0KICAgICAgICBpbmRleCArPSAxCiAgICAgICAgcmV0dXJuIHZhbHVlCgogICAgZGVmIHNlY3Rpb24oZGVwdGg9MCk6CiAgICAgICAgaWYgZGVwdGggPiAxMiBvciB0YWtlKCkgIT0gJ3snOgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdJbnZhbGlkIGludmVudG9yeSBzZWN0aW9uJykKICAgICAgICByZXN1bHQgPSB7fQogICAgICAgIHdoaWxlIGluZGV4IDwgbGVuKHRva2VucykgYW5kIHRva2Vuc1tpbmRleF0gIT0gJ30nOgogICAgICAgICAgICBrZXkgPSB0YWtlKCkKICAgICAgICAgICAgaWYga2V5IGluICd7fT1bXScgb3Iga2V5IGluIHJlc3VsdDoKICAgICAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ0FtYmlndW91cyBpbnZlbnRvcnkgZmllbGQnKQogICAgICAgICAgICBpZiBpbmRleCA8IGxlbih0b2tlbnMpIGFuZCB0b2tlbnNbaW5kZXhdID09ICd7JzoKICAgICAgICAgICAgICAgIHJlc3VsdFtrZXldID0gc2VjdGlvbihkZXB0aCArIDEpCiAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICBpZiB0YWtlKCkgIT0gJz0nOgogICAgICAgICAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignSW52YWxpZCBpbnZlbnRvcnkgZmllbGQnKQogICAgICAgICAgICAjIHN3YW5jdGwgcHJpbnRzIGVtcHR5IHNjYWxhciB2YWx1ZXMgYXMgInJlbW90ZS1pZD0gbmV4dC1rZXk9dmFsdWUiLgogICAgICAgICAgICAjIEtlZXAgdGhlIG5leHQgZmllbGQgdW5jb25zdW1lZC4gUmVxdWlyZSBhIHdoaXRlc3BhY2UgYm91bmRhcnkgc28KICAgICAgICAgICAgIyBtYWxmb3JtZWQgImE9Yj1jIiBpcyBub3QgYWNjZXB0ZWQgYXMgdHdvIHNlcGFyYXRlIGZpZWxkcy4KICAgICAgICAgICAgaWYgaW5kZXggPCBsZW4odG9rZW5zKSBhbmQgKAogICAgICAgICAgICAgICAgdG9rZW5zW2luZGV4XSA9PSAnfScgb3IgKAogICAgICAgICAgICAgICAgICAgIGluZGV4ICsgMSA8IGxlbih0b2tlbnMpCiAgICAgICAgICAgICAgICAgICAgYW5kIHRva2Vuc1tpbmRleF0gbm90IGluICd7fT1bXScKICAgICAgICAgICAgICAgICAgICBhbmQgdG9rZW5zW2luZGV4ICsgMV0gaW4gKCc9JywgJ3snKQogICAgICAgICAgICAgICAgICAgIGFuZCB0ZXh0W21hdGNoZXNbaW5kZXggLSAxXS5lbmQoKTptYXRjaGVzW2luZGV4XS5zdGFydCgpXS5pc3NwYWNlKCkKICAgICAgICAgICAgICAgICkKICAgICAgICAgICAgKToKICAgICAgICAgICAgICAgIHJlc3VsdFtrZXldID0gJycKICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgIHZhbHVlID0gdGFrZSgpCiAgICAgICAgICAgIGlmIHZhbHVlID09ICdbJzoKICAgICAgICAgICAgICAgIHZhbHVlID0gW10KICAgICAgICAgICAgICAgIHdoaWxlIGluZGV4IDwgbGVuKHRva2VucykgYW5kIHRva2Vuc1tpbmRleF0gIT0gJ10nOgogICAgICAgICAgICAgICAgICAgIGl0ZW0gPSB0YWtlKCkKICAgICAgICAgICAgICAgICAgICBpZiBpdGVtIGluICd7fT1bXSc6CiAgICAgICAgICAgICAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ0ludmFsaWQgaW52ZW50b3J5IGxpc3QnKQogICAgICAgICAgICAgICAgICAgIHZhbHVlLmFwcGVuZChpdGVtKQogICAgICAgICAgICAgICAgaWYgdGFrZSgpICE9ICddJzoKICAgICAgICAgICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdUcnVuY2F0ZWQgaW52ZW50b3J5IGxpc3QnKQogICAgICAgICAgICBlbGlmIHZhbHVlIGluICd7fT1bXSc6CiAgICAgICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdJbnZhbGlkIGludmVudG9yeSB2YWx1ZScpCiAgICAgICAgICAgIHJlc3VsdFtrZXldID0gdmFsdWUKICAgICAgICBpZiB0YWtlKCkgIT0gJ30nOgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdUcnVuY2F0ZWQgaW52ZW50b3J5IHNlY3Rpb24nKQogICAgICAgIHJldHVybiByZXN1bHQKCiAgICByZXN1bHQgPSBzZWN0aW9uKCkKICAgIGlmIGluZGV4ICE9IGxlbih0b2tlbnMpOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ1RyYWlsaW5nIGludmVudG9yeSBkYXRhJykKICAgIHJldHVybiByZXN1bHQKCgpkZWYgbnVtYmVyKHJlY29yZCwga2V5LCBkZWZhdWx0PU5vbmUpOgogICAgdmFsdWUgPSByZWNvcmQuZ2V0KGtleSkKICAgIGlmIHZhbHVlIGlzIE5vbmU6CiAgICAgICAgcmV0dXJuIGRlZmF1bHQKICAgIGlmIG5vdCBpc2luc3RhbmNlKHZhbHVlLCBzdHIpIG9yIG5vdCByZS5mdWxsbWF0Y2gocidbMC05XXsxLDI0fScsIHZhbHVlKToKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdJbnZhbGlkIGludmVudG9yeSBjb3VudGVyJykKICAgIHJldHVybiBpbnQodmFsdWUpCgoKZGVmIHBhcnNlX2ludmVudG9yeShvdXRwdXQpOgogICAgaWYgbGVuKG91dHB1dCkgPiA4ICogMTAyNCAqIDEwMjQ6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignSW52ZW50b3J5IHRvbyBsYXJnZScpCiAgICBzZXNzaW9ucyA9IFtdCiAgICBjb21wbGV0ZWQgPSBGYWxzZQogICAgc2VlbiA9IHNldCgpCiAgICBmb3IgbGluZSBpbiBvdXRwdXQuc3BsaXRsaW5lcygpOgogICAgICAgIGlmIG5vdCBsaW5lLnN0cmlwKCk6CiAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgaWYgbGluZSA9PSAnbGlzdC1zYXMgcmVwbHkge30nOgogICAgICAgICAgICBpZiBjb21wbGV0ZWQ6CiAgICAgICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdEdXBsaWNhdGUgaW52ZW50b3J5IHJlcGx5JykKICAgICAgICAgICAgY29tcGxldGVkID0gVHJ1ZQogICAgICAgICAgICBjb250aW51ZQogICAgICAgIGlmIGNvbXBsZXRlZCBvciBub3QgbGluZS5zdGFydHN3aXRoKCdsaXN0LXNhIGV2ZW50ICcpOgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdVbnN1cHBvcnRlZCBpbnZlbnRvcnkgb3V0cHV0JykKICAgICAgICBldmVudCA9IHBhcnNlX21lc3NhZ2UobGluZVtsZW4oJ2xpc3Qtc2EgZXZlbnQgJyk6XSkKICAgICAgICBpZiBsZW4oZXZlbnQpICE9IDE6CiAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ0FtYmlndW91cyBpbnZlbnRvcnkgZXZlbnQnKQogICAgICAgIGNvbm5lY3Rpb24sIHJlY29yZCA9IG5leHQoaXRlcihldmVudC5pdGVtcygpKSkKICAgICAgICBpZiBub3QgaXNpbnN0YW5jZShyZWNvcmQsIGRpY3QpOgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdJbnZhbGlkIHNlc3Npb24gcmVjb3JkJykKICAgICAgICB1bmlxdWVfaWQgPSBudW1iZXIocmVjb3JkLCAndW5pcXVlaWQnKQogICAgICAgIGlmIHVuaXF1ZV9pZCBpcyBOb25lIG9yIHVuaXF1ZV9pZCBpbiBzZWVuOgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdBbWJpZ3VvdXMgc2Vzc2lvbiBJRCcpCiAgICAgICAgc2Vlbi5hZGQodW5pcXVlX2lkKQogICAgICAgIGNoaWxkcmVuID0gcmVjb3JkLmdldCgnY2hpbGQtc2FzJywge30pCiAgICAgICAgaWYgbm90IGlzaW5zdGFuY2UoY2hpbGRyZW4sIGRpY3QpIG9yIGFueShub3QgaXNpbnN0YW5jZShjLCBkaWN0KSBmb3IgYyBpbiBjaGlsZHJlbi52YWx1ZXMoKSk6CiAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ0ludmFsaWQgY2hpbGQgc2Vzc2lvbnMnKQogICAgICAgIGlkZW50aXR5X2tleSA9ICdyZW1vdGUtZWFwLWlkJyBpZiAncmVtb3RlLWVhcC1pZCcgaW4gcmVjb3JkIGVsc2UgJ3JlbW90ZS1pZCcKICAgICAgICBpZGVudGl0eSA9IHJlY29yZC5nZXQoaWRlbnRpdHlfa2V5KQogICAgICAgIGlmIGlkZW50aXR5IGlzIG5vdCBOb25lIGFuZCBub3QgaXNpbnN0YW5jZShpZGVudGl0eSwgc3RyKToKICAgICAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignSW52YWxpZCBwZWVyIGlkZW50aXR5JykKICAgICAgICB2aXBzID0gcmVjb3JkLmdldCgncmVtb3RlLXZpcHMnLCBbXSkKICAgICAgICBpZiBub3QgaXNpbnN0YW5jZSh2aXBzLCBsaXN0KToKICAgICAgICAgICAgcmFpc2UgVmFsdWVFcnJvcignSW52YWxpZCB2aXJ0dWFsIGFkZHJlc3NlcycpCiAgICAgICAgc2Vzc2lvbnMuYXBwZW5kKHsnaWQnOiB1bmlxdWVfaWQsICdjb25uZWN0aW9uJzogY29ubmVjdGlvbiwKICAgICAgICAgICAgICAgICAgICAgICAgICdzdGF0ZSc6IHJlY29yZC5nZXQoJ3N0YXRlJyksICdpZGVudGl0eSc6IGlkZW50aXR5LAogICAgICAgICAgICAgICAgICAgICAgICAgJ2lkZW50aXR5U291cmNlJzogaWRlbnRpdHlfa2V5LCAncmVtb3RlSG9zdCc6IHJlY29yZC5nZXQoJ3JlbW90ZS1ob3N0JyksCiAgICAgICAgICAgICAgICAgICAgICAgICAndmlydHVhbEFkZHJlc3Nlcyc6IHZpcHMsICdlc3RhYmxpc2hlZFNlY29uZHMnOiBudW1iZXIocmVjb3JkLCAnZXN0YWJsaXNoZWQnKSwKICAgICAgICAgICAgICAgICAgICAgICAgICdieXRlc0luJzogc3VtKG51bWJlcihjLCAnYnl0ZXMtaW4nLCAwKSBmb3IgYyBpbiBjaGlsZHJlbi52YWx1ZXMoKSksCiAgICAgICAgICAgICAgICAgICAgICAgICAnYnl0ZXNPdXQnOiBzdW0obnVtYmVyKGMsICdieXRlcy1vdXQnLCAwKSBmb3IgYyBpbiBjaGlsZHJlbi52YWx1ZXMoKSl9KQogICAgaWYgbm90IGNvbXBsZXRlZDoKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCdJbnZlbnRvcnkgcmVwbHkgbWlzc2luZycpCiAgICByZXR1cm4gc2Vzc2lvbnMKCgpkZWYgcmVhZF9ub2RlKG5vZGUpOgogICAgaWYgbm9kZSBub3QgaW4gKCdyaWdhJywgJ21vc2NvdycpOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoJ0ludmFsaWQgbm9kZScpCiAgICBjb21tYW5kID0gWycvdXNyL3NiaW4vc3dhbmN0bCcsICctLWxpc3Qtc2FzJywgJy0tcmF3J10gaWYgbm9kZSA9PSAncmlnYScgZWxzZSBTU0ggKyBbJ3N3YW5jdGwgLS1saXN0LXNhcyAtLXJhdyddCiAgICByZXN1bHQgPSBzdWJwcm9jZXNzLnJ1bihjb21tYW5kLCBjYXB0dXJlX291dHB1dD1UcnVlLCB0ZXh0PVRydWUsIHRpbWVvdXQ9MjUsIGNoZWNrPUZhbHNlKQogICAgaWYgcmVzdWx0LnJldHVybmNvZGU6CiAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCdOb2RlIGludmVudG9yeSBjb21tYW5kIGZhaWxlZCcpCiAgICByZXR1cm4gcGFyc2VfaW52ZW50b3J5KHJlc3VsdC5zdGRvdXQpCgoKZGVmIG1haW4oKToKICAgIGlmIG9zLmdldGV1aWQoKSAhPSAwIG9yIGxlbihzeXMuYXJndikgIT0gMiBvciBzeXMuYXJndlsxXSBub3QgaW4gKCdyaWdhJywgJ21vc2NvdycpOgogICAgICAgIHByaW50KGpzb24uZHVtcHMoeydzdGF0dXMnOiAnZXJyb3InLCAnZXJyb3InOiAnSW52YWxpZCBpbnZlbnRvcnkgcmVxdWVzdCd9KSkKICAgICAgICByZXR1cm4gMQogICAgbm9kZSA9IHN5cy5hcmd2WzFdCiAgICB0cnk6CiAgICAgICAgc2Vzc2lvbnMgPSByZWFkX25vZGUobm9kZSkKICAgICAgICByZXN1bHQgPSB7J3N0YXR1cyc6ICdvaycsICd2ZXJzaW9uJzogVkVSU0lPTiwgJ25vZGUnOiBub2RlLCAnc2Vzc2lvbnMnOiBzZXNzaW9ucywKICAgICAgICAgICAgICAgICAgJ29ic2VydmVkQXQnOiBkYXRldGltZS5ub3codGltZXpvbmUudXRjKS5pc29mb3JtYXQoKX0KICAgIGV4Y2VwdCAoT1NFcnJvciwgUnVudGltZUVycm9yLCBWYWx1ZUVycm9yLCBzdWJwcm9jZXNzLlRpbWVvdXRFeHBpcmVkKToKICAgICAgICByZXN1bHQgPSB7J3N0YXR1cyc6ICdlcnJvcicsICdub2RlJzogbm9kZSwgJ2Vycm9yJzogJ05vZGUgaW52ZW50b3J5IHVuYXZhaWxhYmxlJ30KICAgIHByaW50KGpzb24uZHVtcHMocmVzdWx0LCBlbnN1cmVfYXNjaWk9VHJ1ZSwgc2VwYXJhdG9ycz0oJywnLCAnOicpKSkKICAgIHJldHVybiAwIGlmIHJlc3VsdFsnc3RhdHVzJ10gPT0gJ29rJyBlbHNlIDEKCgppZiBfX25hbWVfXyA9PSAnX19tYWluX18nOgogICAgcmFpc2UgU3lzdGVtRXhpdChtYWluKCkpCg=='
HASH = 'a6cb68cb626fe21cfcfc773318b751d47aeb177762e9d2ebbeda1c939a647d02'
BASE = Path('/usr/local/sbin')
READER = BASE / 'tolf-admin-sessions'
MARKER = '# TOLF read-only admin sessions v1'
ROOT_BLOCK = '''
# TOLF read-only admin sessions v1
if [ "${1:-}" = admin-sessions ]; then
    [ "$#" -eq 2 ] || exit 1
    case "$2" in riga|moscow) ;; *) exit 1 ;; esac
    exec /usr/local/sbin/tolf-admin-sessions "$2"
fi
'''
SSH_BLOCK = '''
# TOLF read-only admin sessions v1
if [[ "${SSH_ORIGINAL_COMMAND:-}" =~ ^admin-sessions[[:space:]]+(riga|moscow)$ ]]; then
    exec sudo -n /usr/local/sbin/tolf-provision-root admin-sessions "${BASH_REMATCH[1]}"
fi
'''


def patch(source, block):
    if MARKER in source:
        if block.strip() not in source:
            raise RuntimeError('Existing admin integration differs')
        return source
    anchor = 'set -euo pipefail\n'
    if source.count(anchor) != 1 or '/usr/local/sbin/tolf-' not in source:
        raise RuntimeError('Unsupported provisioning script')
    return source.replace(anchor, anchor + block + '\n', 1)


def atomic(path, data, info=None):
    fd, name = tempfile.mkstemp(prefix='.'+path.name+'-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(name, (info.st_mode & 0o777) if info else 0o755)
        os.chown(name, info.st_uid if info else 0, info.st_gid if info else 0)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    if os.geteuid() != 0 or socket.gethostname() != 'EDISLV':
        raise SystemExit('Run as root on Riga EDISLV')
    with open('/var/lock/tolf-provision.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        reader = base64.b64decode(PAYLOAD)
        if hashlib.sha256(reader).hexdigest() != HASH:
            raise RuntimeError('Payload checksum mismatch')
        compile(reader, str(READER), 'exec')
        planned = {READER: reader}
        for name, block in [('tolf-provision-root', ROOT_BLOCK), ('tolf-provision-ssh', SSH_BLOCK)]:
            path = BASE/name
            planned[path] = patch(path.read_text(), block).encode()
            subprocess.run(['/bin/bash', '-n'], input=planned[path], check=True)
        backup = Path('/root/tolf-admin-sessions-backup-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid()))
        backup.mkdir(mode=0o700)
        original = {}
        for path in planned:
            original[path] = (path.read_bytes(), path.stat()) if path.exists() else None
            if path.exists():
                shutil.copy2(path, backup/path.name)
        print('Backup:', backup, flush=True)
        try:
            for path, data in planned.items():
                atomic(path, data, original[path][1] if original[path] else None)
            run = subprocess.run([str(READER), 'riga'], capture_output=True, text=True, timeout=30, check=True)
            report = json.loads(run.stdout)
            if report.get('status') != 'ok' or report.get('node') != 'riga':
                raise RuntimeError('Riga inventory validation failed')
        except Exception:
            for path, old in original.items():
                if old is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic(path, old[0], old[1])
            print('Previous files restored.', flush=True)
            raise
        print('OK: read-only session inventory installed. VPN configuration and sessions unchanged.')
        print('Riga sessions:', len(report['sessions']))
        run = subprocess.run([str(READER), 'moscow'], capture_output=True, text=True, timeout=30)
        try:
            report = json.loads(run.stdout)
            if run.returncode or report.get('status') != 'ok':
                raise ValueError('Moscow unavailable')
            print('Moscow sessions:', len(report['sessions']))
        except (ValueError, KeyError):
            print('Moscow inventory unavailable; do not interpret this as zero sessions.')


if __name__ == '__main__':
    main()
