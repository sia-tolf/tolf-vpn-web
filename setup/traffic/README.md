# VPN traffic accounting — implementation checkpoint

Status: the UK ledger, local RADIUS decoder/durable spool and regression tests
are prepared. A guarded first-stage Moscow loopback receiver installer is
available. Moscow receiver installation and its durable UDP test have been
confirmed by the operator. VPN accounting and delivery to UK are not enabled.
Admin UI integration and the
guarded installers follow verification of the current node accounting setup.

## Scope and direction

Attribute VPN payload bytes to the ingress session exactly once. Upload means
bytes received from the VPN user; download means bytes sent to the VPN user.
GRE/WireGuard transit counters and physical-interface counters are not inputs.
This prevents counting Moscow–Riga transit twice. These payload totals are not
a replacement for the hosting provider's billable physical-link statistics.

The UK remains the control plane: account attribution, historical storage,
period queries, administration authorization and sorting live there. Nodes
produce session accounting events, retain a local spool and deliver them over
an authenticated restricted channel. Collectors must not change authentication
methods or routing, and browser code must not submit accounting events.

## Ledger contract

`tolf_traffic.Ledger` uses SQLite tables in the UK account database. `ingest`
takes a source node fixed by the authenticated collector, not by event data.
Each event has `eventId`, `protocol`, `sessionId`, `username`, `observedAt`,
`upload`, `download`, and `kind`. Nodes are Moscow/Riga and protocols are
IKEv2/AnyConnect. UTC-aware observation timestamps are mandatory.

Session identifiers must be unique across daemon restarts, persist across
rekeys and collector restarts, and distinguish simultaneous sessions. An event
identifier is stable on retry. Reusing it with different data is rejected.

Kinds:

* `start`: fresh session, both cumulative counters zero.
* `baseline`: a session already active when collection begins; existing bytes
  are saved as the baseline and excluded from newly collected history.
* `interim`: monotonically increasing cumulative payload counters.
* `stop`: final cumulative counters, closing the stream.

An unknown stream requires a start/baseline. A counter reset requires a new
stream; it is never silently treated as new usage. A failed batch rolls back
all its changes. Old snapshots are acknowledged as stale without adding bytes;
the node spool must retain source order and deliver start before interim/stop.
Identical repeated events are harmless. Closed streams reject changed counters.

The account mapping is resolved at stream start and frozen. IKEv2 usernames
are looked up in VPN access, managed users and Windows device records.
AnyConnect certificate CNs are looked up in the device registry. Ambiguous or
unknown identities remain unattributed and are reported separately, not assigned
to an arbitrary account. Deleted accounts and revoked device records do not
delete historical ledger entries.

## Periods and sorting

Queries use half-open intervals `[start,end)` with timezone-aware boundaries,
up to 366 days. UI boundaries should be converted from the administrator's
selected local dates into UTC. The initial detailed daily breakdown explicitly
uses UTC dates; do not label it as local days without conversion.

The delta is assigned to the timestamp of its accounting update. Period
boundaries therefore have the granularity of the interim reporting interval;
the ledger does not invent per-second traffic distribution inside that interval.
Collectors must expose freshness, gaps, initial collection time and node errors
to the UI. A zero without coverage must not be shown as confirmed zero usage.

`ranked_accounts` sorts the whole account population before applying pagination.
Supported sorts are total/upload/download/lastActivity, ascending or descending,
with account ID as a stable tie-breaker. Zero-traffic accounts are included.
`summary` provides totals, node/protocol/device breakdown, UTC days and separately
unattributed totals. Text search will be integrated into the account listing's
existing authenticated SQL query before sorting and pagination.

## Node sources being verified

strongSwan EAP-RADIUS accounting supplies totals across all CHILD SAs and a
session ID that survives IKE rekey. Verify whether it is enabled, where the
accounting receiver runs, and whether interim updates and durable detail records
are available before deploying a collector. Do not sum current IKE SA snapshots
as historical usage.

ocserv disconnect scripts expose final 64-bit byte counters. Preserve the existing
personal-routing hooks when adding accounting. Interim polling or accounting
must use the same logical session identity and counter semantics as the final
record. Confirm compilation features and active configuration first.

References:
https://docs.strongswan.org/docs/latest/plugins/eap-radius.html#_accounting
https://github.com/openconnect/ocserv/blob/master/doc/sample.config

## Verification

`radius_accounting.py` decodes authenticated strongSwan Accounting-Requests,
combines Octets/Gigawords into 64-bit counters, retains Event-Timestamp when
provided and otherwise uses receipt time minus Acct-Delay-Time. strongSwan
6.0.3 source does not emit Event-Timestamp: examples containing it may show
attributes added by FreeRADIUS. For native messages the retry identity uses
session elapsed time/status/counters rather than the generated wall timestamp;
the spool retains the first committed observation when retries arrive later.
This timestamp is an approximation, not a claimed exact traffic event time.
It acknowledges only after a FULL-synchronous SQLite transaction commits.
The ordered spool survives receiver restarts; deletion requires a subsequent
explicit UK acknowledgement. Deployment must use a dedicated loopback listener
and a random local secret, never a public authentication listener. Existing active sessions still
require an explicit baseline policy before activation.

`install-moscow-receiver.py` is generated by `build.py`. It checks root, the
Moscow br-lan address and ocserv configuration before mutations. It refuses
unknown installations and occupied ports, creates a private secret
and durable spool, enables a procd service on 127.0.0.1:18130 and verifies an
authenticated UDP request plus its committed database row. It stops the
receiver before deleting the synthetic test record, then starts it again.
On failure it disables the new service and retains failed artifacts in the
printed backup directory. It does not enable strongSwan accounting, restart VPN
services, modify ocserv hooks or configure delivery to the UK. The spool is
only a node buffer; historical attribution and administration remain on UK.
The compatibility updater accepts only the exact previously deployed receiver
hash and unchanged service definition, preserves the secret and database, and
restores the previous receiver on failure. It refuses an accounting-enabled
configuration. Its signed UDP test now omits Event-Timestamp, like strongSwan.

Activation blocker: strongSwan 6.0.3 `send_start()` invokes
`eap_radius_handle_timeout(ike_sa->get_id(...))` unconditionally if the initial
Accounting-Start fails. Setting `accounting_close_on_timeout = no` only prevents
closure on interim failures; it does not fix start failures. Do not claim the
native accounting path is independent of VPN availability. Resolve this before
activation (or select a VICI collector that handles final CHILD counters/rekeys).
Source: https://github.com/strongswan/strongswan/blob/6.0.3/src/libcharon/plugins/eap_radius/eap_radius_accounting.c

`python3 -m unittest discover -s tests/traffic -v`

Twenty-five tests cover native messages without Event-Timestamp, retry time
preservation, a real loopback UDP receiver, wrong-server preflight,
packet authentication, 64-bit RADIUS counters, durable spooling,
storage failure without acknowledgement, duplicates, retries, final counters, pre-existing baselines,
reordered events, explicit counter resets, reconnects, persistence, atomic batch
rollback, node/protocol separation, ambiguous attribution, frozen account mapping,
global sorting and pagination, timezones and half-open period boundaries.
