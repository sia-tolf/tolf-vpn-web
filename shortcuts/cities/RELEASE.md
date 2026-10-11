# English city names: release pending iCloud shares

Public artifacts are in ru/, en/, lv/. Import names and VPN titles are always
TOLF Moscow and TOLF Riga. Menus are always English; website instructions remain RU/EN/LV.

The two AEA1-signed files contain no account credentials or certificates.
Share each city command from Apple's Shortcuts app and record its iCloud ID in
CITY_SHARES in js/ios-vpn-buttons.js. The published shares must each be
checked by downloading the iCloud record and comparing menu actions and VPN
bindings against the corresponding plist.

Do not deploy the English-name UI/backend until both links have been verified.
Missing links deliberately do not fall back to the old generic TOLF shortcut.

After both shares exist:
1. Verify name, menu language, native VPN titles, Cisco target, and terminal
   Nothing / Home Screen / Nothing actions of each shared record.
2. Run Python test_mobileconfig.py and test_shortcuts.py and Node
   ios-shortcut-link.cjs, anyconnect-ui.cjs, quick-anyconnect.cjs.
   The UI tests use synthetic IDs from ios-city-share-fixture.cjs.
3. Back up and deploy the changed tolf_oc_shortcuts, tolf_oc_webclips,
   and tolf_oc_mobileconfig modules to /opt/tolf-api, restart and check health.
4. Publish the matching frontend with the two real iCloud links.
5. Verify clean installation and both cities on a real iPhone/iPad.
   Existing installed Russian-named profiles/shortcuts are not renamed remotely;
   reinstall the profile and add its English-named command.

Shared MobileConfig payload IDs remain stable per device and entry point,
so reinstalling a city replaces that city's profile, not the other city.
