#!/usr/bin/env python3
"""Synchronize the dedicated Moscow New York listener certificate over pinned SSH."""
import subprocess,hashlib
SSH=['ssh','-T','-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10']
NY=SSH+['-i','/opt/tolf-mcp/us_ed25519','-o','UserKnownHostsFile=/opt/tolf-mcp/us_known_hosts','root@162.252.174.201']
MOS=SSH+['-i','/opt/tolf-mcp/moscow_ed25519','-o','UserKnownHostsFile=/opt/tolf-api/.ssh/known_hosts','root@92.243.66.204']
archive=subprocess.run(NY+['tar','-chf','-','-C','/etc/letsencrypt/live/tolf-oc-us-relay','fullchain.pem','privkey.pem'],capture_output=True,check=True,timeout=25).stdout
# Archive remains in memory and is never printed or written on the relay host.
receiver="""set -eu
umask 077
dir=/etc/ocserv-ny-moscow
mkdir -p "$dir"
stage=$(mktemp -d "$dir/.cert.XXXXXX")
trap 'rm -rf "$stage"' EXIT
tar -xf - -C "$stage"
openssl x509 -in "$stage/fullchain.pem" -noout -checkhost oc-us-moscow.tolf.is >/dev/null
openssl x509 -in "$stage/fullchain.pem" -noout -checkend 604800 >/dev/null
openssl x509 -in "$stage/fullchain.pem" -pubkey -noout >"$stage/cert.pub"
openssl pkey -in "$stage/privkey.pem" -pubout >"$stage/key.pub"
cmp -s "$stage/cert.pub" "$stage/key.pub"
if cmp -s "$stage/fullchain.pem" "$dir/fullchain.pem" && cmp -s "$stage/privkey.pem" "$dir/privkey.pem"; then exit 0; fi
cp "$stage/fullchain.pem" "$dir/fullchain.pem"
cp "$stage/privkey.pem" "$dir/privkey.pem"
chmod 600 "$dir/"*.pem
if test -S /var/run/occtl-ny-moscow.socket; then
 /usr/sbin/ocserv -t -c "$dir/ocserv.conf" >/dev/null
 occtl -s /var/run/occtl-ny-moscow.socket reload >/dev/null
fi
"""
subprocess.run(MOS+['sh','-c',__import__('shlex').quote(receiver)],input=archive,check=True,timeout=25)
print('Moscow certificate synchronized')
