# Test-account session control

This bridge is deliberately limited to account **26**, VPN EAP identity
`user_0888048cac6e44d28aed9857aa31e9ed`. It is not general customer control.

`install-riga-test-control.py` runs as root on EDISLV. It backs up the two
existing provisioning dispatchers, adds narrowly validated commands, and
installs `/usr/local/sbin/tolf-admin-test-control`. The existing inventory
helper and VPN credentials are untouched. Post-install checks only list native
VICI sessions on both nodes; failure restores the previous files. Installation
does not send a terminate request. No daemon restarts are needed.

## Transport and selection

Riga connects directly to `/var/run/charon.vici`. Moscow uses a fixed SSH command
with strict host-key verification and `/usr/bin/socat STDIO
UNIX-CONNECT:/var/run/charon.vici`. There is no Python dependency on Moscow.
The binary codec follows the official strongSwan VICI specification:
https://github.com/strongswan/strongswan/blob/master/src/libcharon/plugins/vici/README.md

The command `admin-test-sessions NODE` exposes only established test sessions,
with IKE unique ID and both SPIs. It requires an explicit EAP identity match;
an IKE identity alone cannot authorize termination.

`admin-test-disconnect NODE ID INITIATOR_SPI RESPONDER_SPI` refreshes the native
inventory, checks all fields and the hardcoded test identity, then terminates
only that IKE unique ID. The list and terminate use one transport connection;
a daemon restart closes that transport. No configuration-name or wildcard
termination is used. The implementation relies on strongSwan IKE unique IDs
not being reused within one daemon lifetime (apart from theoretical uint32
wraparound). It does not offer atomic compare-and-terminate by SPI because
VICI does not provide that operation.

A failure or lost response is not retried. Successful termination is followed
by another inventory query. Automatic client reconnection may create a new
session; this command does not suspend access. Do not use disconnect as a
permanent access ban.

The web API and UI must separately enforce the admin role, origin/CSRF checks,
selection freshness and audit logging before exposing these commands. This
installation alone adds no browser control and is the node-readiness stage.

Build: `python3 setup/admin/nodes/build-control.py`
Tests: `python3 -m pytest tests/admin/nodes/test_control.py -q`
