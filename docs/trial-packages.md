# One-time 1 GB trial

Only an explicit trial signup (password or Passkey) or confirmed authenticated
`POST /account/trial-package` enrolls an account. Ordinary registrations are not
backfilled. Each account receives 1,000,000,000 bytes once, without an expiry.
Admins, protected/imported accounts and accounts with paid traffic cannot claim.
Registration, marker and grant share a transaction. Repeated claims return the
existing package without restoring its balance. Deletion and recreation uses a
new account identity; this is an account limit, not a verified-person limit.

The trial wallet starts at the current server usage counter. It consumes trial
traffic before paid traffic; paid-only accounting is unchanged. Counters only
advance, so counter resets do not refill packages. Traffic reported beyond the
available entitlement is recorded as unfunded and is settled before a new paid
credit. It is not charged against that later purchase. The public API exposes
only the authenticated account's settled balance and sends no-store headers.
The visible billing page polls every 15 seconds, pauses when hidden and keeps
its last confirmed balance on transient failures. It never resets the paid form.

The UK root delivery timer runs every 15 seconds; SQLite settlement runs as the
existing `tolfa` API user. It sends only public authenticated identities, a
90-second lease and API IPv4 addresses to Riga, Moscow and New York over the
existing strictly verified SSH connections. Native agents poll every 5 seconds.
Only unpaid explicit trial recipients are enrolled in this forwarding gate.
After any positive real paid credit, trial restrictions are removed and the
existing paid access policy applies. This does not enable general paid quota
limits or the proposed 256 Kbps fallback. Sandbox credits do not restore access.

The native gate reads authenticated IKE SAs through VICI and OC workers through
occtl. It matches IKE SPI plus peer address and stable OC tunnel interface
indices. It writes only the dedicated `inet tolf_trial_budget` nft table. It does
not restart VPN services or change credentials, profiles, global routing or other
firewall tables. The first-party API TCP/443 remains reachable for balance and
payment status. An expired delivery lease closes only its enrolled trial cohort.
An inventory/application error retains existing rules and retries. New sessions
are gated after discovery, not before tunnel establishment.

Accounting uses the existing periodic server collectors (normally about a minute)
and then delivery/native polling. Exhaustion is therefore asynchronous: this is
not a byte-exact hard cap and a high-rate client can exceed 1 GB before reports
arrive. New sessions have an additional short discovery interval. Trial grant
and public identity tombstones deliberately survive deletion while native access
revocation is pending; they contain no private credentials and cannot restore a
removed account. Human-chosen legacy aliases are not gated because of reuse.

Installation sources are in `setup/trials`. Keep backups and source hashes;
`install_api_patch.py` narrowly updates billing, feature flags and module setup.
Install `tolf_trial_packages.py` beside the API, the native agent with
`vici_readonly.py` on VPN nodes, and root `tolf_trial_budget_sync.py` on the UK
control plane. Start native agents before enabling claims. Rollback disables
claims/delivery, removes only the dedicated nft table and restores backed-up API
sources; it must preserve recorded grant/consumption rows.

Validation: `python -m unittest discover -s tests/trials -v` with FastAPI installed,
`node tests/trials/frontend.cjs`, plus existing account-management checks. Production
installation tests do not issue grants, add paid credits or delete real users.
