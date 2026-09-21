# Optional account passwords

Adds a second sign-in method to the same TOLF users and sessions. No email or
phone number is collected. User-chosen usernames are case-insensitive ASCII,
3–32 characters. Internal account UUIDs and VPN credentials remain independent.

The shared `/auth/` screen provides EN/RU/LV registration, login, recovery,
Web Crypto password generation, editable passwords, password-manager autocomplete,
and explicit saving of credentials/recovery codes. Secrets are not put in browser
storage. The optional downloaded text file contains secrets; its UI says to keep
it private. Password controls appear only after `/password/capabilities` is live.
Main portal and quick setup link to the shared screen. Quick setup retains its
server/platform selection while authenticating.

## Server module

The additive installer appends a module import to the deployed API; it never
replaces existing main.py handlers. It checks the schema, takes a consistent
SQLite backup, preserves file ownership, restarts `tolf-api.service`, and verifies
capabilities. Failure restores the previous code. It deliberately does not restore
the database automatically, which could erase concurrent account changes.

Run as root on London / EDISUK, not on Riga or Moscow:

    python3 /root/install-password-auth.py

Build that single-file installer with `python3 setup/password-auth/build.py`.
Use an immutable commit URL and verify its SHA-256 before executing it.

Only new accounts choose password registration in v1. Existing Passkeys still
work and password accounts can add Passkeys using the existing account UI.
Recovery for a password account requires username + current recovery code.
It changes the password, rotates the recovery code, and revokes existing account
sessions/pending challenges in one transaction. VPN profiles and Passkeys remain.
The existing account recovery-code regeneration works for either account type.

Passwords use a per-user random salt and scrypt N=2^17, r=8, p=1. This follows
[OWASP's scrypt baseline](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
KDF concurrency is limited to two per worker (~256 MiB). Deploy with sufficient
memory for the API worker count. Persistent limits apply per account, client IP,
and globally, before KDF work. Do not configure the reverse proxy/ASGI server to
trust arbitrary caller-supplied forwarding headers. Cookies match the existing
Secure/HttpOnly/SameSite=Lax session contract. Account-deletion cleanup uses a
SQLite trigger because the older API does not always enable foreign keys.

## Checks

    python3 tests/password-auth/test_password_auth.py
    node tests/password-auth/browser.cjs
    node tests/quick/state.cjs
    node tests/quick/browser.cjs

After deployment, use a new test account in Windows Chrome: register with a
chosen username, edit a generated password, save the recovery details, sign out
and sign in, then reset using the code. Confirm the old password/code fail, the
new ones work, and a Windows device can be created through the existing workflow.
No production test accounts are created by the installer.
