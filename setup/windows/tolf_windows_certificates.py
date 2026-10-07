"""UK issuance and revocation of independent Windows device certificates."""
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from fastapi import HTTPException
from tolf_windows_ca import Authority

ROOT = Path('/var/lib/tolf-api/windows-certificates')
CA = Path('/etc/tolf-windows-client-ca')

def path_for(device):
    return ROOT / (str(uuid.UUID(device)) + '.json')

def atomic(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(value, handle)
            handle.flush(); os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)

def exists(device):
    return path_for(device).is_file()

def record(device):
    data = json.loads(path_for(device).read_text())
    if data['deviceId'] != str(uuid.UUID(device)) or data['state'] != 'active':
        raise HTTPException(410, 'Windows certificate was revoked')
    return {**data, 'certificate': base64.b64decode(data['certificate'], validate=True),
            'encrypted_key': base64.b64decode(data['encrypted_key'], validate=True)}

def rpc(ctx, action, row, issued=None):
    if action not in {'apply', 'remove'}: raise ValueError('Invalid certificate operation')
    device = str(uuid.UUID(row['id']))
    node, mode = row['server'], row['local_id']
    from tolf_windows_routes import selection
    selection({'server': node, 'localId': mode})
    authority = Authority(CA)
    data = {}
    if issued:
        certificate = x509.load_pem_x509_certificate(issued['certificate'])
        data = {'certificate': issued['certificate'].decode(), 'ca': authority.cert.public_bytes(serialization.Encoding.PEM).decode(),
                'publicKey': certificate.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()}
    if 'windows_certificate_rpc' in ctx:
        return ctx['windows_certificate_rpc'](action, row, data)
    command = ['/usr/bin/ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
               '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile='+ctx['RIGA_KNOWN_HOSTS'],
               '-i', ctx['RIGA_KEY'], ctx['RIGA_USER']+'@'+ctx['RIGA_HOST'],
               'windows-certificate ' + ' '.join([action, device, node, mode or 'default'])]
    try:
        result = subprocess.run(command, input=json.dumps(data), text=True, capture_output=True, timeout=90)
        response = json.loads(result.stdout)
        if result.returncode or response.get('status') != 'ok' or response.get('deviceId') != device or response.get('server') != node or response.get('localId') != mode:
            raise ValueError('Certificate provisioning was not confirmed')
        return response
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(503, 'Windows certificate service unavailable; retry later') from exc

def ensure(ctx, row):
    path = path_for(row['id'])
    if not path.exists():
        issued = Authority(CA).issue(row['id'])
        atomic(path, {**{key: value for key, value in issued.items() if key not in {'certificate', 'encrypted_key'}},
                      'certificate': base64.b64encode(issued['certificate']).decode(),
                      'encrypted_key': base64.b64encode(issued['encrypted_key']).decode(),
                      'deviceId': row['id'], 'state': 'active'})
    issued = record(row['id'])
    certificate = x509.load_pem_x509_certificate(issued['certificate'])
    if certificate.not_valid_after_utc <= datetime.now(timezone.utc):
        raise HTTPException(410, 'Windows certificate expired; create a new Windows device')
    rpc(ctx, 'apply', row, issued)
    return issued

def revoke(ctx, row):
    if not exists(row['id']): return
    # A deletion stays pending until the gateway confirms removal.
    rpc(ctx, 'remove', row)
    path = path_for(row['id'])
    data = json.loads(path.read_text())
    data['state'] = 'revoked'
    data.pop('encrypted_key', None)
    data['revoked_at'] = datetime.now(timezone.utc).isoformat()
    atomic(path, data)

def bundle(issued):
    authority = Authority(CA)
    pfx, password = authority.bundle(issued)
    return pfx, password, authority.cert.public_bytes(serialization.Encoding.DER)
