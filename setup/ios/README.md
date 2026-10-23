# Protocol-qualified iOS VPN names
AnyConnect profile, managed connection, signed Shortcut target and website setup target use TOLF <English city> AnyConnect.
IKEv2 defaults use TOLF <English city> IKEv2 plus the existing routing suffix. Legacy default names submitted by cached pages are normalized server-side; explicit custom names retain their text and acquire the protocol suffix if missing.
apply_profile_labels.py applies the narrow change to the existing /opt/tolf-api/tolf_profiles.py module, including Install profile (RU/LV/EN) on the Apple installation page. It is idempotent and leaves signing, UUIDs, authentication, routing and Android output unchanged.
Deploy only the vpn_name function from setup/anyconnect/tolf_oc_shortcuts.py into the installed shortcut module; do not replace unrelated runtime shortcut changes. Back up both installed modules first, then restart tolf-api. VPN daemons do not need restarting.
Tests: tests/ios/test_profile_names.py against TOLF_PROFILES_SOURCE, tests/ios/profile-name-ui.cjs, AnyConnect mobileconfig and shortcut suites, quick-anyconnect.cjs.
Already installed profiles and shortcuts retain their prior names until reinstalled. Previously issued token payloads remain immutable; create a fresh profile to obtain the new label.
