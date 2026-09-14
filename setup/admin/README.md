# TOLF administration, inventory phase

The approved target is `/admin/`: account/device inventory, live sessions, session termination and reversible suspension, followed by invitations/promos and an action log.

This first install provides account and Windows-device inventory, the existing managed-user registry and a role-change audit log. It does **not** interpret `vpn_active` or `windows_devices.state='active'` as a connected session. It does not expose passwords, recovery hashes, Passkey credential IDs/public keys, or session tokens. Existing VPN creation, rotation and deletion endpoints are not reused as disconnect/suspend actions.

All inventory endpoints enforce the existing authenticated account AND a server-side administrator role on every request. No web endpoint grants roles. Root selects a managed-account number during installation or uses `--grant-number N`; `--revoke-number N` takes effect on the next request. The known account database schema is checked before files change. The installer backs up API source files, preserves unrelated changes, verifies the new capabilities endpoint and restores previous files if startup fails. Two additive admin tables are intentionally not removed on rollback.

Build: `python3 setup/admin/build.py`. Install the generated `install-tolf-admin.py` as root on London EDISUK. No VPN-node change is part of this phase.

## Pending node integration

The deployed London `provision_on_riga` permits only create/profile/rotate/delete/grant-moscow/revoke-moscow. There is no supported live-session, terminate or reversible-suspend operation. Before implementing these, inspect the actual Riga forced-command wrapper and root provisioning helper, the Riga-to-Moscow sync mechanism and how manual/linked protected users are stored. Do not work around the existing SSH allowlist with arbitrary remote commands.

The eventual node action must return per-node results, preserve credentials for resume, prevent provisioning/sync from reactivating suspended users, terminate only matched IKE SAs, and report partial/unconfirmed changes. Moscow availability must not be inferred from a successful Riga operation. Administrator self-lockout and protected users need explicit behavior before enabling state-changing controls.
