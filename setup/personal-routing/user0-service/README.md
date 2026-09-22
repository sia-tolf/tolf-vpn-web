# Local user0 rule, Moscow OpenWrt

This deliberately narrow release persists `user0: delfi.lv -> Moscow`, including
subdomains. It is **not** the multi-account API enforcement system. UK revision 1
still says Riga/pending; this local override neither reads nor acknowledges it.
Before connecting API delivery, explicitly reconcile that stored desired rule.

The checked-in core is a snapshot of the bounded pilot. `service.py` supplies
continuous operation, ownership/recovery, a private DNS PID file, health probes,
and procd integration. Only an explicit authenticated VICI EAP ID `user0` in
`ikev2-eap-domain` and an installed matching CHILD_SA in 10.10.10.0/24 are accepted.
IP, inbound reqid, and SPI all match packet rules. Multiple children during rekey
are supported; ambiguous VIP ownership aborts and withdraws the rule. Missing EAP
identity does not fall back to the untrusted IKE identity.

DNS .53:53 for this session is translated to the private .53:1053 dnsmasq, which
forwards to the unchanged Unbound .53:53. Only this service's translated DNS
conntrack entries are deleted on withdrawal. The main dnsmasq is not restarted.
Private dnsmasq dies with its controller on Linux (PR_SET_PDEATHSIG). On controller
failure procd restarts it and startup removes owned stale rules/connections. A
short disruption until restart is possible; this is not zero-downtime failover.
Normal service stop performs cleanup and leaves the existing base policy active.

Rules and fw4 input exceptions are reconciled every two seconds. Whole-table
loss triggers a clean restart; a fw4 reload restores only owned input exceptions.
DNS and the mark-to-br-lan route are checked every fifteen seconds. If health or
VICI fails the service withdraws its override and procd retries. Status is a local
runtime heartbeat, not an API applied-revision acknowledgement or a proof of
end-to-end web delivery. No existing routes, nft includes, shared DNS configs,
credentials, API database, or unrelated rules are edited.

Domain tracking is IPv4 and ordinary VPN DNS only. It cannot classify arbitrary
DoH or traffic that bypasses this resolver. Shared CDN IPs can also route other
sites for user0. The nft set is limited to 4096 entries and each element has a
24-hour lifetime; this is a stale-entry bound, **not exact DNS TTL tracking**.
Client DNS answers are capped at 300 seconds. DNS caches from before installation,
long-lived connections, set expiry, or restart may temporarily use the base route.
This is a routing preference, not a leak-prevention or isolation boundary.

Deployment: stage `core.py`, `service.py`, `tolf-user0-routing.init`, `install.py`
from one pinned commit and verify the provided hashes, then run `python3 install.py`
as root on Moscow. Installer refuses existing installations, checks dependencies,
route/DNS/VICI/kernel support, starts service, and enables boot only after a fresh
heartbeat. Startup failure stops/cleans/removes the new installation if cleanup
succeeds; recovery files are retained if cleanup fails.

Rollback (retain files for inspection):

```sh
/etc/init.d/tolf-user0-routing disable
/etc/init.d/tolf-user0-routing stop
```

Diagnostics:

```sh
cat /var/run/tolf-user0-routing/status.json
nft list table inet tolf_user0_routing
logread -e tolf-user0-routing
```

Live evidence prior to this implementation: 1293 matched packets used Moscow
br-lan and zero used Riga during the bounded override test; a separate DNS trial
successfully populated delfi.lv and subdomain addresses. The new service itself
still needs on-node install, reconnect, stop and boot verification. Local tests
exercise identity/rule generation and mocked lifecycle failures, not a live
OpenWrt kernel or procd.
