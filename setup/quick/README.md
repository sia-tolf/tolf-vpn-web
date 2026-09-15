# Quick setup v1

The frontend `/quick/` is enabled from the main registration button only when
`/quick-setup/capabilities` returns version 1. Existing invitations keep their flow.
A new registration creates the normal secure HttpOnly login session after successful
Passkey verification; the recovery code is shown before VPN preparation.

IP recommendation uses the existing first-party endpoint. Russia -> Moscow,
else/unknown -> Riga, with a manual override; no latency override in this flow.
Defaults: Riga Local ID `sr`, Moscow empty Local ID, server DNS/routing, On Demand off.
Windows retains its existing native installer; Store integration is not included.

Run the generated `install-quick-setup.py` as root on **EDISUK (London)**.
The installer checks API source anchors before changes, backs up files, atomically
updates them, restarts only the API, probes capabilities and rolls files back on failure.
It does not create VPN users or change running VPN sessions during installation.
The install adds the empty `quick_setups` table and `quick-locks` directory.

Moscow no longer needs a promo: authenticated mobile create/profile requests use the
existing `grant-moscow` operation under the existing account-operation lock before
provisioning. This maintains Riga/Moscow synchronization and retains the node-side
administrative suspension guard. It does not bulk grant existing users or restore
suspended credentials. Windows already grants its independent device permission.
Historical promo records and redemption functionality are preserved.

Setup metadata is durable and keyed to the authenticated account. Windows retries
reuse a server-stored UUID. Mobile retries detect existing VPN access and request a
profile with unchanged credentials. Once a request is reserved, its device/node are
fixed; other configurations remain accessible in My VPN. No profile URL, password or
recovery code is stored in browser storage or the setup table. A resumed setup issues
a fresh delivery link for the same access; it does not claim a verified connection.

Tests use mock provisioning functions and browser API responses, never live accounts.
No installation or success claim is inferred from clicking the download link.
