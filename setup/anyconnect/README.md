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
* `GET /oc/access/devices`: authenticated, current account only.
* `POST /oc/access/devices`: issuance deliberately unavailable until node activation.

The registry includes per-device certificate serials, distinct CNs, expiry,
revocation state and encrypted private keys. It does not issue credentials during
installation. The pilot policy endpoints and UI remain in place at this stage.

## Required activation and next stages

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
