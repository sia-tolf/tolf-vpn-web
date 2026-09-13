# Existing VPN user invitations

The administrator issues a one-use invitation for an existing manual EAP user on
Riga. The recipient registers a Passkey or signs in at vpn.tolf.is, then explicitly
links the existing VPN access. Registration's recovery-code flow is unchanged.
One website account has one primary VPN login. An account which already has VPN
access cannot replace it through an invitation; its Windows devices are separate.

## Installation

Install the same packaged `install-invitations-v1.py` on **Riga first**, then
**London**. Verify the downloaded file against the checksum for the pinned commit.

Riga (EDISLV): `python3 /root/install-invitations-v1.py riga`

London (EDISUK): `python3 /root/install-invitations-v1.py london`

The installer checks exact patch anchors and syntax, makes backups in
`/root/tolf-invitations-backup-*`, and restores changed files if installation fails.
The London service is restarted and its new capabilities endpoint checked.
The Riga installer does not reload StrongSwan, rewrite credentials, or alter routes.
The London database gets an additive `vpn_imports` table. Rollback of files does not
restore a stale database snapshot over live account activity.

## Issue or revoke an invitation

Run as root on Riga:

```sh
/usr/local/sbin/tolf-invite issue user0
```

The output is the personal invitation URL. Give it only to that user's owner.
It expires after 24 hours. Issuing another invitation for the same unlinked user
revokes prior unused invitations. To revoke unused invitations explicitly:

```sh
/usr/local/sbin/tolf-invite revoke user0
```

Use the actual login (for example `user0_ipad`). Generated website logins
`user_<32 hex>` and `u_<32 hex>` cannot be invited. The credential file must be
`/etc/swanctl/conf.d/user-LOGIN.conf` with a single matching EAP identity and secret.
Neither command outputs a VPN password. Do not include invitation URLs in public
issues or logs. The URL token is a bearer secret.

## Persistence and recovery

Riga keeps the UUID-to-login binding and hashed invitation in
`/var/lib/ike-users/web-bindings/bindings.db` (root-only directory).
London keeps the claim state in `vpn_imports` in the existing TOLF database.
Back up both databases along with the existing credentials and profile identities.
Both bindings survive reboot.

Claiming does not rename or rewrite the credential file or stable profile identity
files. Subsequent profile and password operations resolve the website UUID to the
original login. Existing profiles keep working until the user changes the password.
Normal unlinked website and Windows device UUIDs retain the original provisioning
logic. A claimed manual user cannot be linked to another website account.

Root's provisioning lock serializes remote claims with provisioning. London's
existing cross-process account lock serializes linking with VPN/account operations.
London reserves a pending record before the remote claim. If the response is lost,
retry the same invitation: Riga's claim is idempotent for the same UUID. Pending
claims block provisioning and account deletion until resolved. The invitation is
kept in session storage during registration/login; if storage was unavailable or
the tab was closed, reopen the original URL to retry. Invalid/expired invitations
which caused no remote change release the pending reservation.

For ordinary users, deleting VPN access retains the mapping so a later explicit
creation uses the same login. Account deletion also releases the mapping after the
credential has been removed and invalidates its consumed invitations. For protected
users `user0` and `user0_ipad`, VPN and account deletion are blocked. Account deletion
is rejected **before** deleting Windows devices. Contact the administrator for an
intentional protected-account deletion; this feature supplies no protection bypass.

## Tests

```sh
python3 -m unittest discover -s tests/invitations -v
node tests/invitations/frontend.cjs
```

Python tests need FastAPI and HTTPX. Browser tests need Playwright Chromium.
Tests cover authentication/origin, expiry, one-use/concurrent claims, retries after
a lost response, preservation of credentials, protected deletion, installer guards,
and the narrow-screen invitation flow in English, Russian and Latvian. Real Passkey
registration and SSH/sudo behavior must also be checked after server installation.
