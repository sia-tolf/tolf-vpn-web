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

### Riga expansion checkpoint, 3 October 2026

Operator confirmed foundation installer success: /etc/ocserv/uk-foundation-backup.tbo71n6k,
UK CA fingerprint unchanged, CRL number 2 dated 3 October, next update 10 October.
Personal device enforcement and UK multi-ingress integration are still pending.
The operator identified /usr/local/sbin/tolf-openconnect-sr.sh as the Riga
table creator, tolf-oc-dns-refresh.sh as the RU domain-set updater and
tolf-oc-dns-watch.py as a watcher currently scoped to pilot IP 10.19.0.195.
No yt_domains4 set is present in the observed Riga ruleset. Their full sources
are required before integration so a table rebuild cannot silently remove
personal rules and YouTube mode cannot be acknowledged without enforcement.

`tolf_oc_nodes.py` is a tested, staged coordinator, not yet included in the UK
installer or installed API. It requires all node acknowledgements for device
registration/policy, compensates partial changes (including a lost reply),
attempts CRL refresh and disconnect at every node even if one is unavailable,
and separates per-node session errors from disconnected states. Integration
must reconcile stored policies on all nodes after compensation failures.

Operator output confirms Debian ocserv 1.3.0, parallel plain password and
certificate authentication (`enable-auth = certificate`). HAProxy accepts
`oc-riga.tolf.is` SNI at 188.214.39.114:443 and forwards TCP to
127.0.0.1:8443 with PROXY v2. ocserv DTLS listens at 188.214.39.114:443/UDP.
The pool is 10.19.0.0/24, DNS 10.254.0.53. Riga main exits via ens3;
tables 102/119 exit via gremoscow, peer 10.33.0.1. The existing
`inet tolf_oc_sr` sets ru4/ru_domains4 mark RU destinations 0x190 to table 119.

The authorized target is one UK-issued certificate per device accepted at every
activated ingress, initially Moscow and Riga, with distinct Cisco connections.
UK remains the only account, policy, signing and revocation control plane.

`install-riga-foundation.py` installs public UK CA trust, CRL enforcement and a
systemd five-minute signed CRL sync timer. It pins the CA DER fingerprint,
retains existing CA certificates and auth/listener/routing settings, rejects
unrelated existing CRL settings, validates ocserv config and restores files on
failure. Public files are in /etc/ocserv/tolf-uk; backups are private directories
under /etc/ocserv. Sync verifies signature, dates and nondecreasing CRL number.
This foundation alone does not install the Riga personal device registry,
policy/session APIs or the two-ingress UI; these are subsequent stages.

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
| POST /oc/access/devices/{id}/import | Active owned device; new one-time two-hour grant and separately displayed password |
| POST /oc/access/devices/{id}/setup-link | Active owned device; authenticated owner creates a 24-hour bearer setup link, replacing older setup links for that device |
| GET /oc/access/setup/{token} | No login; valid link returns label and connection details; never consumes the link or returns a password/private key |
| POST /oc/access/setup/{token}/claim | No login; vpn.tolf.is Origin required; atomically consumes setup link and returns a two-hour PKCS12 import grant and password |
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
   a retry button. Revoke sits in the same row as the device selector and access state;
   additional access sits on the right of the section title in the wide layout. A separate colored status badge shows
   checking, connected, disconnected or verification failure from the existing
   authenticated session poll. Pending issuance and revocation retain lifecycle
   labels. The selector contains device names only; step 3 and 4 headings name
   the selected device. Switching devices clears confirmation until rechecked.
   Routine polls retain the last result until a new result arrives, so the
   fixed-width status does not flash checking every ten seconds.
   Every active access offers local setup or transfer to another device. Transfer
   destination is initially unselected; clicking local setup reveals its steps,
   while transfer reveals the delivery controls. In the wide layout the device
   selector has the same half-row width as the local setup button below it.
   creates a 24-hour bearer installation URL. A half-width, ellipsized field has
   the overlapping-square copy icon and local confirmation; the equal-width
   Share link button is to its right. Destination controls have a 22px top gap.
   The recipient opens `anyconnect-setup.html#<token>` without an account.
   The fragment is read by local JavaScript; referrer policy is no-referrer and
   requests omit account cookies. Metadata reads never consume the link.
   Getting the certificate consumes the setup link exactly once and starts a
   two-hour single-use package download. The recipient follows installation,
   connection creation, certificate import and VPN activation, with RU/EN/LV
   instructions. Account management and routing remain with the owner.
   Replacing a link, expiry, revocation, certificate expiry or account deletion
   invalidate delivery. Existing installed VPN access survives link expiry.
   Link hashes only are stored in `oc_setup_links`; plaintext tokens and import
   passwords are not stored. New feature availability is `guestSetup: true`.
   Existing `?ocDevice=` URLs still require owner sign-in; new transfer URLs do
   not use that old mechanism. Ownership transfer to a recipient account is
   outside this stage.
3. Select External Control → Prompt in Cisco Secure Client, then add the
   connection using the AnyConnect link. Return to the website for step 4;
   enable VPN only after importing the certificate. Manual server address:
   `oc.tolf.is:4443`. A short External Control reminder precedes the add button.
4. Get the certificate and copy the password using the adjacent copy icon.
   The copy confirmation appears above its icon. Import into AnyConnect or
   download/import the .p12 manually. Use one method per single-use grant.
   The download action fetches the package and saves an octet-stream Blob with
   the .p12 filename instead of navigating Safari to the certificate URL.
   Repeat saves reuse the encrypted package in page memory; object URLs are
   cleared on device/account/grant change, expiry and page hide.
   On iPhone/iPad, share the saved file from Files to Cisco Secure Client.
   For manual connection setup, select the imported certificate in the
   connection's settings after import.
5. Enable VPN with the default group. The website confirms that device's session
   before showing a green dot. Change Auto/RU/LV/YT on the website.

Windows uses manual PKCS12 import into Current User → Personal and manual
connection setup. Mobile links do not confirm installation or a VPN session.
Import passwords are never included in URIs. Connection names have a unique
device suffix and at most 24 characters.
All steps use the same content inset. Import/download actions share a full-width
row with equal-width columns and inherit the site's standard button styles.
All explanatory paragraphs and list items use the same normal text color,
inherited font family, 14px size, 400 weight and 1.55 line height on account and
guest setup pages. Errors and connection statuses retain their semantic colors.
Device selection and revoke share one full-width row with equal heights;
additional access is in the section header in the wide layout.
The status has no frame or background and uses a nine-pixel colored dot.
Narrow-screen layout refinement is deferred until the wide layout is accepted.
The Get certificate button matches the width of the Import into AnyConnect button.
Certificate preparation is disabled and dimmed until the user explicitly confirms
"Connection added" in the preceding step. Opening the Cisco URI alone
does not confirm completion. This gate applies both to account setup and guest
setup links; confirmation is cleared when selecting another device, changing
accounts or leaving the page. It records user confirmation, not verification
that the connection was saved inside Cisco Secure Client.
After confirming connection creation, the user can select Certificate already
imported for this device's existing access. This skips bundle issuance/import,
does not consume guest setup links, and instructs selecting the same certificate
in the new connection settings. Get certificate remains available for recovery.
The site records a user confirmation; it does not inspect the Cisco certificate
store. This choice resets on device/account changes, Add again and page exit.
Before confirmation, mobile connection and Continue actions share one row with
equal-width columns, with connection on the left and confirmation on the right.
Short action labels keep the wide-layout buttons on one line at the site's
standard height: "Add to AnyConnect" and "Connection added".
After confirmation, the Continue control and Cisco connection link are replaced
by a noninteractive completion panel. Add again restores the connection step and
locks certificate actions until reconfirmation, retaining any unexpired bundle.
The overview username comes from the authenticated account's `vpn.username`,
as in IKEv2; it is hidden if that field is absent. Device certificate CNs remain
in certificate selection, session checks and routing commands, and are not
shown as account usernames or as standalone setup instructions.

Cisco URI reference:
https://www.cisco.com/c/en/us/td/docs/security/vpn_client/anyconnect/Cisco-Secure-Client-5/admin/guide/cisco-secure-client-admin-guide-new/ac-on-mobile-devices-intro/t_automate_anyconnect_actions_using_the_uri_handler.html

## Validation

```sh
python -m unittest discover -s tests/anyconnect -v
node tests/anyconnect-ui.cjs
node tests/anyconnect-guest-ui.cjs
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
