# TOLF administration, inventory phase

The approved target is `/admin/`: account/device inventory, live sessions, session termination and reversible suspension, followed by invitations/promos and an action log.

Version 1.1 provides account and Windows-device inventory, the existing managed-user registry, a role-change audit log, and read-only live sessions from Riga and Moscow through the installed node gateway. Each node has its own success/error state and observation timestamp. Identity-to-account mapping is display-only; ambiguous identities remain unmatched. Polling rechecks administrator privileges after the remote response. Install the Riga gateway before updating London. It does **not** interpret `vpn_active` or `windows_devices.state='active'` as a connected session. It does not expose passwords, recovery hashes, Passkey credential IDs/public keys, or session tokens. Existing VPN creation, rotation and deletion endpoints are not reused as disconnect/suspend actions.

All inventory endpoints enforce the existing authenticated account AND a server-side administrator role on every request. No web endpoint grants roles. Root selects a managed-account number during installation or uses `--grant-number N`; `--revoke-number N` takes effect on the next request. The known account database schema is checked before files change. The installer backs up API source files, preserves unrelated changes, verifies the new capabilities endpoint and restores previous files if startup fails. Two additive admin tables are intentionally not removed on rollback.

Build: `python3 setup/admin/build.py`. Install the generated `install-tolf-admin.py` as root on London EDISUK. No VPN-node change is part of this phase.

## Pending node integration

The deployed London `provision_on_riga` permits only create/profile/rotate/delete/grant-moscow/revoke-moscow. There is no supported live-session, terminate or reversible-suspend operation. Before implementing these, inspect the actual Riga forced-command wrapper and root provisioning helper, the Riga-to-Moscow sync mechanism and how manual/linked protected users are stored. Do not work around the existing SSH allowlist with arbitrary remote commands.

The eventual node action must return per-node results, preserve credentials for resume, prevent provisioning/sync from reactivating suspended users, terminate only matched IKE SAs, and report partial/unconfirmed changes. Moscow availability must not be inferred from a successful Riga operation. Administrator self-lockout and protected users need explicit behavior before enabling state-changing controls.

## Combined sessions (2026-10-20)

The account link now opens /admin/; the legacy /admin/v1.3.html includes the same Traffic and Limits tabs. Limits remain in their existing non-enforcing mode.

A root timer collects read-only IKEv2 and AnyConnect inventories from Riga, Moscow and New York every 30 seconds. It writes an atomic allow-listed snapshot to /var/lib/tolf-api/admin-vpn-sessions.json, mode 0600, owned by tolfa. The API rejects snapshots older than 90 seconds and retains administrator checks before and after collection. Root SSH keys remain inaccessible to the API process. No VPN service restart is required.

Deploy tolf_admin.py to /opt/tolf-api/, preserving the previous file for rollback. Install the adjacent tolf-admin-vpn-sessions.service and .timer in /etc/systemd/system/, run systemctl daemon-reload, start the service once, enable/start the timer, then restart tolf-api. The collector uses existing fixed infrastructure keys and host-key files in its target map; it is specific to this deployment. Verify both protocol statuses for all nodes and snapshot freshness before publishing.

Traffic page fix: deploy setup/admin/tolf_oc_traffic.py to /opt/tolf-api/tolf_oc_traffic.py alongside the combined sessions timer. The page reads the shared snapshot, never polls each device through the controller. Traffic accounting calculations are unchanged. Exact period boundaries are displayed; requests abort after 25 seconds.
