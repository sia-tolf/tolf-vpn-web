# Protocol-qualified iOS VPN names
AnyConnect profile, managed connection, signed Shortcut target and website setup target use TOLF <English city> AnyConnect.
IKEv2 defaults use TOLF <English city> IKEv2 <ROUTE>. The routing suffix is always present and uppercase: empty Moscow Local ID, Riga sr and New York auto are shown as AUTO; explicit SR, LV, RU (and the existing New York YT mode) retain their meaning. Local ID values are never changed by naming. Legacy default names submitted by cached pages are normalized server-side; explicit custom names retain their text and acquire the protocol suffix if missing.
apply_profile_labels.py applies the narrow change to the existing /opt/tolf-api/tolf_profiles.py module, including Install profile (RU/LV/EN) on the Apple installation page. It is idempotent and leaves signing, UUIDs, authentication, routing and Android output unchanged.
Deploy only the vpn_name function from setup/anyconnect/tolf_oc_shortcuts.py into the installed shortcut module; do not replace unrelated runtime shortcut changes. Back up both installed modules first, then restart tolf-api. VPN daemons do not need restarting.
Tests: tests/ios/test_profile_names.py against TOLF_PROFILES_SOURCE, tests/ios/profile-name-ui.cjs, AnyConnect mobileconfig and shortcut suites, quick-anyconnect.cjs.
Already installed profiles and shortcuts retain their prior names until reinstalled. Previously issued token payloads remain immutable; create a fresh profile to obtain the new label.

## AnyConnect control icon binding
The setup page downloads the authenticated /oc/access/devices/{device}/shortcuts/control.shortcut for the selected ingress, rather than a historical fixed-name iCloud share.
The signed command name, its Cisco VPN target, the WebClip run-shortcut name and the full Home Screen label are identical, including AnyConnect and ordinary spaces (no TOLF- rewrite).
The site wizard uses a new progress key so a previous confirmation of a stale iCloud command cannot skip the new command step.
Installed commands are not automatically removed or renamed. Replacement/duplicate behaviour in Apple's Shortcuts remains a separate investigation.

## Visible command-import step
The command download action remains visible after the user confirms import, so a missing command can be added again without clearing browser storage.
Wizard state is namespaced as tolfIosImportV4 to discard earlier confirmations that may have preceded actual import.
The setup explains that the profile installs the Home Screen launcher, not the shortcut itself; a downloaded signed .shortcut file must be opened and added separately.
The website cannot inspect the iPad Shortcuts collection. A user acknowledgement never counts as an automatic device-side verification.

## iCloud restoration (current delivery policy)
Direct .shortcut download is removed from the setup UI. Only validated iCloud shares may be linked.
Historical f480fd5427e6404aa122684df1aee6fb and 54c7236b5b2d4812a7fae50f387b75dd were inspected through their public iCloud records and shortcut plists: they target TOLF Moscow and TOLF Riga, not the protocol-qualified current VPN names.
CITY_SHARES is intentionally null until the owner publishes updated commands with the exact current target names. Do not re-enable these historical shares or silently rename VPN profiles to fit them.
While awaiting publication, the site states that icon setup is unavailable and permits profile installation without an icon. It does not mark the shortcut installed or expose a file fallback.
After obtaining an updated owner-provided share, verify its public name and all Cisco/WFVPN targets against CITY_SHORTCUT_NAMES before enabling the matching city.
