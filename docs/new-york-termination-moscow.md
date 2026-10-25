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

## Stable Moscow comparison target

The customer comparison while remaining on New York VPN failed because
speedtest.vpn.tolf.is resolved to 10.21.0.1, which only exists while an ordinary
Moscow pool tunnel is active. There were only 10.24 clients at that point.
Added an independent unused loopback /32, 10.250.82.1, managed by an enabled
startup service. Moscow VPN DNS maps the measurement hostname to that address.
No client pool address is permanently assigned or modified. The remote public
DNS record remains unchanged; this override is scoped to the Moscow resolver.
A control client on the actual New York ingress resolved the hostname through
10.254.0.54 and completed TLS, CORS ping, 1 MiB download and 1 MiB upload to
the Moscow measurement server. This restores the comparison, not a speed fix.

## TUN queue policy integration correction, 2026-10-25

On the customer iPad TUN interface, tx_dropped reached 59,560 while the GRE
interface counters showed no drops. The existing queue policy recognized
vpns-mow followed by digits and applied txqueuelen 2000. The new listener's
vpns-mowN prefix failed that suffix validation, leaving the default queue at 500.
Added an explicit vpns-mowN branch before the original branch; numeric validation
and existing Moscow behavior remain unchanged. Applied to the active interface
without a service restart. New control sessions automatically received queue 2000.

The temporary iPad BBR /32 route was explicitly removed and its rollback timer
stopped, so subsequent comparisons use CUBIC. A control download transferred
49,655,738 bytes with zero TUN drops at 47.6 Mbps; seven parallel requests hit
the short eight-second deadline. That limited load does not establish the iPad's
new maximum throughput or prove elimination of drops at its higher rate.

The attempted 500-versus-2000 mutation test was abandoned; no conclusion from an
A/B load comparison is claimed. patch-ny-tun-queue.py records the deployed change.

## Per-session iPad performance observer, 2026-10-25

Remaining TUN drops persisted after the queue-prefix correction. The deployed
worker hash was traced through profile changes to the O2/DTLS16 build, which
already preserves TUN batch32 and DTLS readiness polling. It was not replaced.

A separate UK diagnostic VPN with temporary per-address BBR delivered 159,809,456
bytes in 10.18 s (125.62 Mbps); its worker used 57.2% of one core and TUN dropped
zero packets. Its connected UDP socket had SO_RCVBUF 8,388,608 and SO_SNDBUF
524,288 with zero socket drops. Temporary identity, routes and timers were cleaned.
These results do not reproduce the customer's higher-rate iPad drops.

Installed metadata-only /usr/libexec/tolf-ny-ipad-performance under procd,
restricted to the authorized iPad certificate CN and the NY/Moscow socket. It
records process CPU, TUN byte/packet/drop counters, and connected UDP socket queue
and drop counters. No payloads, certificates or credentials are captured. Five
second inventory refresh; samples every second, or every 250 ms when active
traffic exceeds 10 Mbps. Logs rotate every five minutes and retain 24 files under
/root/tolf-diagnostics/ny-ipad-performance. PID start time and interface index
prevent comparisons across recycled processes/interfaces. No routes, priorities,
socket buffers or queue sizes are changed by the observer.

Syntax, procd launch and real control-session metric reads were validated.
The control-session test invoked the sampling function directly, without changing
the production CN filter. A customer-session load sample is still required before
attributing remaining losses to a specific queue or applying another change.

### 2026-10-25: distinguish scheduler delay from worker I/O delay

The iPad measurement at approximately 07:23 UTC showed 193.2/39.7 Mbps
in the browser. The matching Moscow observer session recorded 956 new TUN
transmit drops in three intervals, with worker CPU at 61.18%, 75.40%, and
57.84% of one core. The connected UDP receive socket recorded no drops.
These counters locate local losses but do not establish the exact TUN
drop branch or why the worker was delayed.

The observer now records per-worker /proc/PID/schedstat runtime and
runnable wait deltas, plus per-vCPU steal time from /proc/stat.
This distinguishes time waiting for a CPU from time not runnable.
Existing CN scope, bounded log rotation, and metadata-only collection remain.
No VPN worker, routing, queue size, socket buffer, or scheduling priority changed.
The observer alone was restarted; the iPad worker PID remained 24284.
Verification: deployed syntax compiled, procd running, new JSONL records
contained schedulerRuntimeMs, schedulerWaitMs and hostStealPercent.
Initial idle records are not evidence for behavior during a speed test.
