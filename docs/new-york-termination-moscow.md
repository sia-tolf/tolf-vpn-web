# New York entry through Moscow — VPN termination

Activated 2026-10-24. Supersedes the transparent TCP/UDP VPN relay described in earlier commits.

For source IPs classified as Russian, existing request_catalog chooses
oc-us-moscow.tolf.is:4443 (92.243.66.204). Other source IPs keep
oc-us.tolf.is:4443. The country gate, device identity, logical profile/shortcut
name TOLF New York AnyConnect and profile UUIDs are unchanged.

## Data path

The dedicated ocserv-ny-moscow instance terminates TLS/DTLS locally on Moscow's
secondary public IP. It uses the existing certificate authority, shared per-device
eligibility registry and CRL, with a separate 10.24.0.0/24 lease pool and
vpns-mowN interfaces. Ordinary Moscow remains on .32 with its existing pools.
No account routing preference is changed when New York is selected.

The external-exit helper always sends eligible 10.24 leases through greus,
fwmark 0x800/table 198, regardless of the device's ordinary Moscow routing mode.
The New York moscow-exit service supplies return routes and NAT for 10.24.
A host route for 10.250.81.1 through greus permits the existing internal speed test.
The normal Moscow pool routing, including the selectable US mode, is unchanged.

The old relay retains TCP 80 solely for the NY-hosted ACME HTTP-01 renewal.
It no longer forwards VPN TCP or UDP. No router static route is required.

## Operations

Moscow:
- /etc/init.d/ocserv-ny-moscow (enabled, startup 97)
- /etc/ocserv-ny-moscow/ocserv.conf and certificate pair
- /var/run/occtl-ny-moscow.socket
- /usr/libexec/tolf-oc-users combines both Moscow daemons
- accounting, recovery and collection query the aggregate inventory
- device revocation disconnects both daemons and denies runtime leases
- CRL synchronization reloads both daemons
- /etc/init.d/tolf-external-exit must restart after helper code changes

UK:
- certificate is transferred NY-to-Moscow through pinned management SSH;
  no private material is printed or stored on UK
- tolf-sync-ny-moscow-certificate.timer every six hours; service validates
  hostname, expiry and matching public keys before deploying/reloading
- tolf_oc_live reads aggregate accounting
- tolf_oc_nodes merges logical New York status received from Moscow
- tolf_admin moves the relayed sessions into New York's inventory

NY:
- /opt/tolf-vpn-project/tolf-node-installer/ny_moscow_exit.py includes 10.24
- existing tolf-moscow-exit service persists route and NAT

Final Moscow source is in moscow-changes.json. prepare-moscow.py records the
initial transition; do not rerun it over final files without reviewing the
subsequent session/CRL/persistence integration captured in the final snapshot.
Certificate files and account databases are intentionally excluded.

## Validation

A temporary diagnostic identity, removed after each test, connected from UK
using legacy AES-GCM DTLS. Lease came from 10.24, the VPN terminated on Moscow,
and the external address was 162.252.174.201. After waiting beyond the background
refresh interval, DNS on 10.254.0.54 answered and the internal NY measurement
endpoint returned HTTP 200 for ping, 1 MiB download and 1 MiB upload.

The background exit daemon initially retained the previous in-memory code;
restarting it resolved the periodic route reset. This was caught before asking
the customer to reconnect. No claim of an iPad speed improvement is made until
the customer's own measurement.

Five unit tests cover fixed NY egress, preserved ordinary Moscow behavior,
revoked eligibility, accounting for the new pool, and logical session reporting.
Existing RU endpoint selection tests still apply.

## Rollback

Moscow originals are in /root/tolf-backups/ny-termination-20261024.
UK originals are in /opt/tolf-api/ny-termination-backup-20261024.
NY original script is ny_moscow_exit.py.before-termination-20261024.
Before restoring helper code, stop/disable the dedicated listener and certificate
timer. Restore the old relay file only if transparent forwarding is deliberately
wanted; otherwise disable the RU gate to return new profiles to direct NY.
Restore Moscow helper files, restart external-exit, reapply device rules,
restore UK modules and restart tolf-api. Existing direct NY clients are unaffected.

## Measurement DNS correction

The customer iPad established ECDHE-RSA DTLS on the new listener but could not
resolve speedtest-us.vpn.tolf.is: Moscow dnsmasq rebinding protection removed
the private A answer. The initial probe used an explicit IP override and missed
this dependency. Added only this hostname to the existing rebind_domain list;
global rebinding protection remains enabled. Re-tested via the actual VPN DNS
10.254.0.54, resolved 10.250.81.1, validated TLS by hostname, and received HTTP
200 with CORS for ping, 1 MiB download and 1 MiB upload without a DNS override.
