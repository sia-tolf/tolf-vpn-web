# Personal routing: storage stage

This stage installs only desired-policy storage on EDISUK. It does not change
DNS, nftables, swanctl, profiles or VPN node credentials. Do not merge the
frontend feature into main until its separate save/load API and node enforcement
are integrated and verified.

Authenticated GET /vpn/routing-rules returns the policy and revision.
Authenticated POST accepts exactly revision and routingRules (riga/moscow/usa
domain arrays). A trusted website Origin is mandatory for writes. Maximum 200
domains, subdomains included; overlapping domains in different exits are rejected.
USA is not yet available. IP/CIDR rules are not part of this version.

Every saved policy is pending, enforcementAvailable=false, appliedRevision=null.
Never interpret a successful save as successful traffic routing. Identical saves
with the current revision are idempotent; stale revisions receive HTTP 409.
Existing profile generation endpoints do not save these policies.

Install install-storage.py alongside tolf_personal_routing.py and run with the
API virtualenv Python as root on EDISUK. The installer verifies the module hash,
backs up main.py and the live SQLite database, creates an additive table, appends
the integration and restarts only tolf-api. Health and unauthenticated-route
checks follow. On failure, code is rolled back and API restarted; the additive
table is deliberately retained rather than restoring a stale whole database.

Still required: account/VPN deletion lifecycle integration (some existing
connections may have foreign_keys disabled), authenticated node policy delivery,
session identity-to-IP binding, DNS answer tracking, IPv6 handling, shared CDN IP
conflicts, routing/SNAT/return-path handling, offline persistence and application
acknowledgements. No DNS node credential is repurposed by this stage.

Tests:

    python3 -m unittest discover -s tests/routing -p test_personal_api.py -v
    python3 -m unittest discover -s tests/routing -p test_storage_installer.py -v

Installer tests use a temporary database and mocked service/HTTP probes; real
server integration is checked by the installer, not by those unit tests.
