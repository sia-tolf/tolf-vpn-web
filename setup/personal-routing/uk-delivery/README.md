# UK automatic personal-routing delivery: enrolled user0 pilot

This upgrade uses the existing API integration and adds a separate systemd worker.
It is restricted to account `6e4f2559-fa36-410c-8b09-b299055d1ed6` / `user0` and
Moscow `ikev2-eap-domain`, as enforced independently by the node and Riga relay.
Other accounts retain storage-only behavior. No VPN profile or strongSwan config
is changed. Install only after the protocol-2 receiver and Riga gateway have
passed their status probes.

Stage install.py, rollback.py, tolf_personal_routing.py, tolf_routing_delivery.py,
and ../user0-service/policy.py under the name tolf_routing_contract.py. Run the
installer with /opt/tolf-api/venv/bin/python on EDISUK. It checks the storage module
hash and exact SSH settings, verifies the channel as the API service user, backs
up code and SQLite, then briefly stops the API. A guarded transaction migrates
only the known revision-1 delfi.lv-to-Riga preference to revision 2 targeting
Moscow, preserving the already verified live behavior. Unexpected rows abort.
It starts the API and worker and waits for matching node application evidence.

The worker polls every 10 seconds, persists its outgoing intent, and uses bounded
SSH JSON requests. Node revisions are monotonic even across withdrawal and later
recreation of the same account mapping. API revisions are matched through the
stored intent rather than assumed identical to node revisions. A late response
cannot acknowledge newer rules. A node ahead of the control database requires
review. Fresh matching receipts distinguish applied, ready (no eligible session),
pending, conflict (shared destination IP) and unavailable. Receipts expire after
60 seconds. Browser closure does not stop delivery.

Deleted users, deleted VPN mappings, missing preferences or ambiguous ownership
of user0 generate empty rules on the next successful reconciliation. This is
asynchronous, not an instantaneous access-revocation mechanism; VPN access
control remains the responsibility of existing provisioning. With a disconnected
control channel the node keeps its last accepted policy, and the API stops
reporting fresh application. Routing matches IPv4 destinations learned via the
classic VPN DNS path and inherits the receiver's shared-IP, TTL, DNS-cache and
alternative-resolver limitations. This pilot does not cover every entry profile
or every VPN protocol.

Failure restoration disables the delivery worker and restores storage-only API
code. It retains the saved Moscow preference and never replaces the complete
live database. The printed rollback script likewise keeps currently accepted
node rules; it is not a rule-withdrawal operation. It refuses files changed by a
later deployment. Retained schema/helper files deliberately prevent blind
reinstallation after rollback; inspect before retrying.

The frontend remains a separate deployment. Do not claim the live website has
this editor until its feature branch is deployed.
