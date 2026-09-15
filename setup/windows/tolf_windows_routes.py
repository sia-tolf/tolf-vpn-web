"""Windows routing contract and restricted Riga RPC (no VPN passwords)."""
import json
import subprocess
import uuid
from fastapi import HTTPException

MODES = {'riga': ('sr', 'ru'), 'moscow': ('', 'sr', 'ru', 'lv')}
HOSTS = {'riga': 'ikev2-riga.tolf.is', 'moscow': 'ikev2.tolf.is'}


def selection(payload):
    server = payload.get('server', 'riga')
    if not isinstance(server, str) or server not in MODES:
        raise HTTPException(400, 'Unsupported Windows VPN location')
    mode = payload.get('localId', 'sr' if server == 'riga' else '')
    if not isinstance(mode, str) or mode not in MODES[server]:
        raise HTTPException(400, 'Unsupported Windows routing mode')
    return server, mode


def rpc(ctx, action, device=None, server=None, mode=None):
    if action not in ('capabilities', 'apply', 'remove'):
        raise ValueError('Invalid routing operation')
    args = ['windows-routing', action]
    if action != 'capabilities':
        args.append(str(uuid.UUID(device)))
    if action == 'apply':
        selection({'server': server, 'localId': mode})
        args.extend((server, mode or 'default'))
    if 'windows_routing_rpc' in ctx:
        return ctx['windows_routing_rpc'](*args[1:])
    try:
        command = ['/usr/bin/ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                   '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile='+ctx['RIGA_KNOWN_HOSTS'],
                   '-i', ctx['RIGA_KEY'], ctx['RIGA_USER']+'@'+ctx['RIGA_HOST'], ' '.join(args)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=90)
        data = json.loads(result.stdout)
        if result.returncode or not isinstance(data, dict) or data.get('status') != 'ok':
            raise ValueError('Routing operation failed')
        return data
    except (KeyError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(503, 'Windows routing service unavailable; retry later') from exc


def available(ctx):
    # Compatibility: old Riga/sr devices remain usable before node installation.
    try:
        data = rpc(ctx, 'capabilities')
        if data.get('protocol') == 1 and data.get('modes') == {k:list(v) for k,v in MODES.items()}:
            return data['modes']
    except HTTPException:
        pass
    return {'riga': ['sr']}


def apply(ctx, row):
    if not row.get('routing_managed'):
        return
    data = rpc(ctx, 'apply', row['id'], row['server'], row['local_id'])
    if data.get('server') != row['server'] or data.get('localId') != row['local_id']:
        raise HTTPException(502, 'VPN server did not confirm the selected Windows route')
