#!/usr/bin/python3
"""Forced SSH command dispatcher; no shell expansion or account data."""
import os
import re
import sys

command = os.environ.get('SSH_ORIGINAL_COMMAND', '')
controller = '/usr/local/sbin/tolf-oc-riga-devices'
if command == 'tolf-oc-node-health':
    args = [controller, 'health']
elif command == 'tolf-oc-crl-sync':
    # Controller health must run only after synchronization succeeds.
    import subprocess
    result = subprocess.run(['/usr/local/sbin/tolf-oc-riga-crl-sync'],
                            capture_output=True, timeout=60)
    if result.returncode:
        print('{"status":"error","error":"crl_sync_failed"}')
        sys.exit(1)
    args = [controller, 'health']
else:
    match = re.fullmatch(r'tolf-oc-(device|device-remove|session) (tolf-oc-[0-9a-f]{32})(?: (auto|ru|lv|yt))?', command)
    if not match or (match[1] == 'device') != (match[3] is not None):
        print('{"status":"error","error":"command_not_allowed"}')
        sys.exit(1)
    args = [controller, {'device': 'set', 'device-remove': 'remove', 'session': 'session'}[match[1]], match[2]]
    if match[3]:
        args.append(match[3])
os.execv(args[0], args)
