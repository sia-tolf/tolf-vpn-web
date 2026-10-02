# Personal AnyConnect access

UK owns the account/device registry, signing authority, certificate issuance and
revocation. Moscow receives public trust material and enforces access. The
certificate authority is separate from the historical pilot CA.

## Stage 1: UK foundation

Run the hash-verified, self-contained `install-uk-foundation.py` as root on
EDISUK. It uses the existing API environment and service user, preserves the
current account database, backs up `main.py`, and generates a new CA under
`/var/lib/tolf-api/anyconnect`. A rerun must preserve the same CA fingerprint.
The service user can read the encrypted signing key and its local wrapping
password. Neither these files nor device private keys belong in GitHub.

Endpoints installed at this stage:

* `GET /oc/access/capabilities`: foundation version, public CA fingerprint,
  `issuance=false`, `nodeReady=false`.
* `GET /oc/access/ca.pem`: public CA certificate only.
* `GET /oc/access/crl.pem`: signed public revocation list. The UK registry's
  revoked/revoking serials are added atomically under an interprocess lock.
  Existing revocations are retained even if their database rows disappear.
  The seven-day CRL renews on retrieval when less than one day remains; unchanged
  requests return the cached signed list. Moscow must fetch it periodically
  before issuance is enabled. Active-session disconnection still requires the
  next node-control stage.
* `GET /oc/access/devices`: authenticated, current account only.
* `POST /oc/access/devices`: issuance deliberately unavailable until node activation.

The registry includes per-device certificate serials, distinct CNs, expiry,
revocation state and encrypted private keys. It does not issue credentials during
installation. The pilot policy endpoints and UI remain in place at this stage.

## Required activation and next stages

### Moscow public trust and CRL

The confirmed node is OpenWrt; ocserv configuration is
`/etc/ocserv-moscow/ocserv.conf`, control socket
`/var/run/occtl-moscow.socket`, and gateway `oc.tolf.is:4443` on
`92.243.66.32`. The server TLS certificate covers `oc.tolf.is`.

After adding the UK CA to the existing pilot CA bundle, run the hash-verified
`install-moscow-crl.sh <UK CA SHA256>` as root. The installer checks the pinned CA
and its existing trust, verifies the CRL signature and time validity, installs
`/usr/bin/tolf-oc-crl-sync`, adds `crl = /etc/ocserv-moscow/uk-client-ca.crl.pem`,
and installs a tagged five-minute root cron entry. Existing cron jobs and the
pilot CA remain in place. Installer failures restore prior files and reload
ocserv. A successful reload schedules the update; device authentication and
revocation rejection must still be tested before enabling issuance.

The sync rejects lower CRL numbers, conflicting content with the same number,
expired lists and foreign signatures. Unchanged lists do not rewrite flash or
reload ocserv. Fetch/reload errors retain the prior list and cron reports failures
under log tag `tolf-oc-crl`. The last successful fetch time is recorded in
`/tmp/tolf-oc-crl-last-sync`. A killed sync can leave its temporary lock until
reboot or operator cleanup; this must be monitored during node activation.
The public CRL governs new authentication; disconnecting an already connected
revoked device remains part of the subsequent account/device control stage.

Before enabling issuance, Moscow must trust the additional public CA, enforce its
CRL, and support account/device-specific session and routing control. Preserve the
pilot CA. Confirm the server hostname/certificate and TCP/UDP port 4443 from the
running configuration. Connect a separate test device and verify both successful
authentication and rejection after revocation.

After activation, expose short-lived, protected import grants and an authenticated
create/revoke API. PKCS#12 import uses a separate password shown to the logged-in
owner; do not put that password in a URI. The user flow is:

1. Install AnyConnect.
2. Create access for this device.
3. Import the certificate into AnyConnect.
4. Return to the website and add the connection.
5. Enable VPN and confirm this device's session.

Each step needs localized RU/LV/EN instructions and a manual alternative to the
application URI. An imported certificate or an application link alone does not
confirm a working VPN session.

## Checks

`python -m unittest discover -s tests/anyconnect -v`

`python setup/anyconnect/build.py`
