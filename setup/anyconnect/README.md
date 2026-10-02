# Personal AnyConnect access

UK owns accounts, device identities, signing and revocation. Moscow authenticates
certificates and enforces each device's routing. The website provides separate
access per device and ordered RU/LV/EN instructions. Personal access does not
require an IKEv2 profile.

## Deployment checkpoint, 2 October 2026

Operator output confirms UK foundation/public CRL, Moscow trust of the additional
UK CA, CRL enforcement, and personal device control. A health request from UK as
the actual API user `tolfa` succeeded over the forced SSH handler.

Pinned UK CA SHA256 over DER:
`408f0f2281db53f665a81941f0fdc7883254a4f63b3c72f56d4f9fb8d8ce47ac`.

The v2 UK installer adds issuance, import grants, personal routing/session APIs
and revocation. Run the hash-verified `install-uk-foundation.py --activate`
as root on EDISUK. It verifies Moscow as the service user before writing the
activation gate, preserves the CA, backs up code, restarts the API, and checks
capabilities and CRL signature. Failures restore prior code and activation state.

Moscow health continues to return `issuance:false`: Moscow does not issue
certificates. The UK `/oc/access/capabilities` endpoint should report version 2,
`issuance:true`, `nodeReady:true`, and the same fingerprint after activation.
Actual client import, certificate login, independent routing and rejection after
revocation still require operator validation with a newly issued device.

## Interfaces and addresses

| Component | Address or path | Function |
| --- | --- | --- |
| Website | https://vpn.tolf.is | Authenticated device creation and installation instructions |
| API | https://api.tolf.is | UK account and signing control plane |
| API process | `tolf-api`, user `tolfa`, localhost:8000 | Existing FastAPI service |
| Code / database | `/opt/tolf-api` / `/var/lib/tolf-api/tolf.db` | Modules and shared account database |
| Moscow SSH | `root@92.243.66.204` | Restricted commands using the UK provision key |
| VPN gateway | `oc.tolf.is:4443`, `92.243.66.32` | TCP TLS and UDP DTLS; server TLS certificate covers oc.tolf.is |
| ocserv config | `/etc/ocserv-moscow/ocserv.conf` | Certificate authentication, CN OID 2.5.4.3 |
| occtl socket | `/var/run/occtl-moscow.socket` | Session control and reload |
| Tunnel interfaces | `vpns-mow*` | Default 10.21.0.0/24; RU group 10.22.0.0/24; LV group 10.23.0.0/24 |
| VPN DNS | `10.254.0.54` | DNS pushed by ocserv |
| Moscow routing | mark `0x100`, table `main` | Moscow egress |
| Riga routing | mark `0x200`, table `100` | Default via `gre4-riga_gre` |
| Internal measurement | `speedtest.vpn.tolf.is:8444` → `10.21.0.1` | LibreSpeed over VPN, wildcard TLS, DNS rebind exception |

The shared measurement selector chooses an accessible endpoint independently of
the displayed protocol. The internal Moscow address avoids the AnyConnect
gateway's client-side tunnel exclusion. Measurement fallbacks remain in place.

## Modules and state

* `tolf_oc_certificates.py`: create-once RSA CA, distinct RSA device keys,
  clientAuth certificates valid for at most one year, encrypted PKCS8 storage,
  password-protected PKCS12 packaging, signed seven-day CRLs. Import passwords
  have eight characters, with uppercase/lowercase Latin letters and digits.
* `tolf_anyconnect.py`: ownership checks, bounded JSON, idempotent issuance,
  grants, node acknowledgements, routing/session APIs and revocation retry.
  It preserves the application's lifespan and reconciles every 60 seconds.
* `install-template.py` / `build.py`: self-contained UK installer with embedded,
  hash-checked modules; no live credentials are embedded.
* `moscow-devices.sh`: registration, session/IP bindings, ocserv hooks,
  firewall reapplication, personal routing and disconnect enforcement.
* `moscow-remote.sh`: strict forced SSH command allowlist.
* `sync-moscow-crl.sh`: signed CRL synchronization and ocserv reload.
* `js/anyconnect-access.js`: device selection, issuance retry, import/password
  display, localized instructions and revoke.
* `js/transport-selector.js`: selected device's authenticated policy/session
  calls. The green dot requires that device's confirmed session and mode.

UK signing files live in `/var/lib/tolf-api/anyconnect`: directory 0700, files
0600, API-user ownership. `ca-key.pem` is encrypted; `key-password.bin` is its
local wrapping secret. `ca.pem`, `ca.crl.pem`, locks and the fingerprint-bound
`activation.json` gate are also here. Back up this directory with the database
using private server backups. Live signing material and device keys never belong
in GitHub.

`oc_devices` stores owner, request UUID, label, device CN, serial, expiry,
certificate, encrypted key, mode and lifecycle state. `oc_import_grants` stores
hashed bearer tokens and encrypted PKCS12 packages; import passwords are not stored.

## API contract

Responses disable caching. Mutations require an authenticated session and exact
Origin `https://vpn.tolf.is`. Device operations check ownership and use the
existing per-account operation lock.

| Method and path | Behavior |
| --- | --- |
| GET /oc/access/capabilities | Version, CA fingerprint, activation/node readiness |
| GET /oc/access/ca.pem | Public CA only |
| GET /oc/access/crl.pem | Cached signed CRL; renew when less than one day remains |
| GET /oc/access/devices | Current account's summaries; no private material |
| POST /oc/access/devices | `requestId` UUID and `label`; limit eight non-revoked unexpired devices |
| POST /oc/access/devices/{id}/import | Active owned device; new one-time ten-minute grant and separately displayed password |
| HEAD /oc/access/import/{token}.p12 | Availability check without consumption |
| GET /oc/access/import/{token}.p12 | Bearer download; atomic consumption; 410 after expiry/use/revocation |
| GET /oc/access/devices/{id}/policy | Stored acknowledged personal mode |
| POST /oc/access/devices/{id}/policy | `mode`: auto/ru/lv/yt; update database after Moscow ACK |
| GET /oc/access/devices/{id}/session | Actual Moscow session for this device CN |
| POST /oc/access/devices/{id}/revoke | Persist request, invalidate grants, sync CRL, remove/disconnect; 202 pending, 200 acknowledged |

Creation proceeds `pending → active` after node registration. Retrying a request
UUID resumes the same certificate; the UI offers a completion button for pending
devices. Revocation proceeds `active/pending → revoking → revoked`; node failures
leave a persistent retry. Account deletion keeps revocation tombstones and
invalidates grants. Reconciliation also handles expiry and orphan identities.
CRL publication retains old serials even if registry rows disappear.

Import URLs are bearer secrets and do not require website cookies so the client
can download. Reissuing a grant invalidates its previous link. Passwords/links
stay in page memory, clear on account/device change and page hide, and are never
written to browser storage. Deployment access logs should treat import URLs as
credential material.

## Moscow enforcement

Personal CNs are `tolf-oc-` plus 32 lowercase hexadecimal characters.
Desired modes: `/etc/ocserv-moscow/device-modes/<CN>`; per-user settings:
`/etc/ocserv-moscow/config-per-user/<CN>`, limiting each certificate to one
session. Hooks use `/usr/bin/tolf-oc-device-hook` and
`/usr/libexec/tolf-oc-devices`. Live bindings: `/var/run/tolf-oc-devices`.
Unregistered personal identities are refused.

`tolf_oc_devices` at prerouting `mangle + 5` follows the pilot chain at
`mangle - 1`. RU uses Moscow; LV uses Riga; Auto sends RU destination sets
through Moscow and other traffic through Riga; YT adds YouTube destinations to
Moscow. Changes clear only the selected device's conntrack flows. A firewall4
script include rebuilds live rules after reload. Removed IPs enter a drop set
before disconnect; reconnect is blocked. Lease reuse removes stale bindings.

Forced SSH commands: `tolf-oc-node-health`, `tolf-oc-crl-sync`,
`tolf-oc-device <CN> <mode>`, `tolf-oc-device-remove <CN>`,
`tolf-oc-session <CN>`. Pilot commands remain compatible; the personal web UI
does not call the global `/oc-test` policy endpoints. Supplied shell text is
never evaluated.

The Moscow trust bundle retains the pilot CA. Dedicated UK public CA:
`/etc/ocserv-moscow/uk-client-ca.pem`; CRL:
`/etc/ocserv-moscow/uk-client-ca.crl.pem`. A tagged root cron fetches every five
minutes. Sync validates CA pin, signature, time, CRL number and same-number
content; errors retain the prior CRL. Log tag: `tolf-oc-crl`; last successful
fetch: `/tmp/tolf-oc-crl-last-sync`. An interrupted sync can leave its temporary
lock until reboot or cleanup.

## User flow

1. Install Cisco Secure Client (AnyConnect).
2. Create separately named access for the device, or select its existing access.
   After creation the form closes; creating another device requires the explicit
   additional-access button. Routine refresh controls are hidden; recovery offers
   a retry button. Revoke is next to the additional-access action.
3. Request certificate/links and copy the password using the adjacent copy icon.
   On mobile, select External Control → Prompt in Cisco Secure Client before
   using the import link. The copy confirmation appears above its icon.
   Import into AnyConnect or
   download/import the .p12 manually. Use one method per single-use grant.
   The download action fetches the package and saves an octet-stream Blob with
   the .p12 filename instead of navigating Safari to the certificate URL.
   Repeat saves reuse the encrypted package in page memory; object URLs are
   cleared on device/account/grant change, expiry and page hide.
   On iPhone/iPad, share the saved file from Files to Cisco Secure Client.
   The button is labelled “Get certificate”; connection links are explicitly
   described in step 4.
4. Return after successful import and add the connection. Manual address:
   `oc.tolf.is:4443`; use the displayed device CN as the client certificate.
   A short External Control reminder appears immediately before the add button.
5. Enable VPN with the default group. The website confirms that device's session
   before showing a green dot. Change Auto/RU/LV/YT on the website.

Windows uses manual PKCS12 import into Current User → Personal and manual
connection setup. Mobile links do not confirm installation or a VPN session.
Import passwords are never included in URIs. Connection names have a unique
device suffix and at most 24 characters.
All steps use the same content inset. Import/download actions share a full-width
row with equal-width columns and inherit the site's standard button styles.

Cisco URI reference:
https://www.cisco.com/c/en/us/td/docs/security/vpn_client/anyconnect/Cisco-Secure-Client-5/admin/guide/cisco-secure-client-admin-guide-new/ac-on-mobile-devices-intro/t_automate_anyconnect_actions_using_the_uri_handler.html

## Validation

```sh
python -m unittest discover -s tests/anyconnect -v
node tests/anyconnect-ui.cjs
node tests/measurement-targets.cjs
node tests/measurement-regression.cjs
python setup/anyconnect/build.py
for file in setup/anyconnect/*.sh; do sh -n "$file"; done
```

Checks cover cross-account isolation, certificate bundles, idempotency, recovery,
one-time grants, revocation retry, background disconnect on account deletion or
expiry, personal routing, lease reuse, CRL validation, secret clearing and
ignoring stale session responses after logout. Actual mobile import remains an
operator check.
