# Existing VPN access: password verification and administrator invitations

Version 2 adds a self-service form on vpn.tolf.is: **I already have VPN access**.
The user verifies their existing VPN login/password, signs in or registers a Passkey,
and explicitly confirms linking. No URL needs to be generated or sent. Protected
users `user0` and `user0_ipad` still require the administrator invitation below;
knowing their passwords never enables self-service linking.

## Upgrade from the installed v1

Download the pinned `update-invitations-v2.py`, verify its published SHA-256, then run
`python3 /root/update-invitations-v2.py riga` on Riga first and
`python3 /root/update-invitations-v2.py london` on London. The update checks the
installed v1 module checksums and wrapper anchors, backs up changed files, and
restores them on installation failure. The London capabilities endpoint must
report version 2. Existing v1 invitations and bindings remain valid. For a fresh
installation use the packaged v1 installer first, then this update.

## Password verification

Passwords travel in the HTTPS POST body and the SSH process's standard input;
they are never included in the command line or URL. The form clears its password
field immediately and stores only a temporary proof token in session storage.
The API does not store or log passwords and returns `Cache-Control: no-store`.

Riga compares the password against the existing credential using a constant-time
comparison. Verification does not change credentials, profiles, routes or binding.
The root-only registry stores the token hash plus a keyed HMAC credential proof;
`proof.key` must be included in registry backups. A password change invalidates
unclaimed proofs. Proofs expire after 15 minutes, and another website account
cannot reuse a consumed proof. Claiming still requires the website session and
correct Origin. Generated website logins cannot be adopted this way.

Persistent limits: London allows 10 attempts per ASGI client address and 200 total
per 15 minutes; Riga independently allows 10 per VPN username and 200 total.
Forwarded headers are not parsed by this module; actual client attribution uses the
existing ASGI proxy configuration. If the ASGI server sees only a proxy's address,
the per-address limit will be shared. Both limits survive service restarts.

If the remote binding succeeded but its response was lost, retry the saved proof.
If that proof is lost or expires, sign into the **same** website account and verify
the password again. Only an authenticated owner with a pending local claim can
request a recovery proof for an already bound VPN user. A client-supplied account
identifier is never used. Other accounts are directed to Passkey login/recovery.
Protected users continue to use their administrator invitation for retries.

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
Tests cover password verification, protected-user rejection, persistent rate limits, proof invalidation on password change, recovery ownership, authentication/origin, expiry, one-use/concurrent claims, retries after
a lost response, preservation of credentials, protected deletion, installer guards,
and the narrow-screen invitation flow in English, Russian and Latvian. Real Passkey
registration and SSH/sudo behavior must also be checked after server installation.
