# Trial registrations and administrative deletion

Trial status records an explicit registration purpose, not the absence of a
payment. A visitor selects the trial card on the billing page, chooses trial
registration and creates an account with password or Passkey. The marker is
written in the same transaction as successful registration. An existing signed-in
account can explicitly record this choice at `/account/trial-registration`.
Ordinary registrations and unsuccessful attempts are not marked or backfilled.

The 1 GB trial package is granted once per account on explicit trial signup or
through `/account/trial-package`. Free and paid balances remain separate.
See `trial-packages.md` for accounting and the trial-only forwarding gate.
The trial marker persists after a paid purchase and is shown alongside an indication of paid traffic.
Active trial accounts can be filtered in Administration → Accounts, and their total
is shown on the Visits page independently of its page-view period. The registration
marker is removed when its account is deleted.

An administrator can open an ordinary account and delete it by typing its account
number and pressing Delete account. The POST requires the current administrator
role, same origin, JSON, an exact number, target UUID and idempotency request UUID.
Self-deletion, administrator accounts and existing protected accounts are refused.
The existing self-service account deletion and the admin route share the same
deletion function and account-operation lock.

Windows and IKEv2 access are revoked before account credentials and sessions are
deleted. AnyConnect certificate tombstones and import invalidation are committed
with deletion; a targeted reconciliation then revokes only this account's devices.
Unacknowledged ingress revocations are reported as pending and retried by the
existing background worker. A node failure before deletion leaves the account in
place and records a failed job that can be explicitly retried. Payment history is
retained. Requested, failed and completed deletion actions are audited.

The shared deletion transaction enables SQLite foreign-key enforcement, so the
existing cascades also remove SmartDNS accounts and credentials, quick-setup
records and personal routing for the target. Certificate revocation tombstones
and accounting records deliberately have no such cascading relationship.

Lost-response retries use the same request UUID or read its guarded status. A
completed job is not executed again. The frontend requires explicit confirmation;
no production users are deleted by installing this feature or running its tests.

`account_management_patch.py` prepares narrow edits to the installed API entry
point, administration, password registration and AnyConnect reconciliation without
replacing unrelated production changes. Keep before/after hashes and backups,
validate generated code and tests, then restart only `tolf-api.service`.

Validation: `python -m unittest discover -s tests/account-management -v` in the API
environment, and `node tests/account-management/frontend.cjs`.

