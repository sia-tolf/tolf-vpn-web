# Optional iOS Home Screen buttons

Status: implementation prepared on the feature branch; **not deployed to the
production website or VPN API**. The two generic signed candidates are hosted
at `https://config.tolf.is/ios-shortcuts/v1/TOLF-ON.shortcut` and
`https://config.tolf.is/ios-shortcuts/v1/TOLF-OFF.shortcut` for iPhone validation.
They are not the previously verified device-specific exports.

## Behavior

- Main AnyConnect setup and Quick Setup show an unchecked optional checkbox.
- `buttons=true` on the authenticated MobileConfig endpoint adds two removable
  WebClips to the existing certificate + VPN profile. Omission preserves the
  previous profile structure. VPN and certificate payload identities stay stable.
- Green power: **TOLF ON**; red stop: **TOLF OFF**. URLs reference these exact
  space-separated Shortcuts names. Do not substitute the older hyphenated names.
- Save MobileConfig downloads the same authenticated profile with the selected
  option. The profile, certificate and PKCS12 password are never publicly hosted.
- RU/EN/LV instructions show the precise installed VPN name, including device
  label. Generic shortcuts ask for the same VPN in both setup questions.
- ON enables On Demand, then connects. OFF disables On Demand, then disconnects.
  Both finish with Go to Home Screen. The Shortcuts application may open briefly.

## iPhone result: setup picker failed (2026-10-10)

The owner tested the generic ON candidate. iOS shows Configure This Shortcut
and the import-question text, but the VPN row is not tappable. Next simply
continues installation without selecting a connection. Import questions do NOT
provide a usable VPN picker in this tested workflow. The release gate failed.
Do not publish the prepared website instructions or these candidates as working
portable setup. The prior device-bound commands remain the verified baseline.
A successful signature and a visible setup question did not validate selection.

## Binding limitation and release gate

The verified native export includes an iOS-local VPN identifier. It did not match
any active device's production VPN payload UUID. Knowing the visible VPN name
therefore does not establish a portable automatic binding. Do not substitute a
profile UUID or ship the author's private native VPN object as a generic shortcut.

`build-public.py` derives only the tested actions, removes both native VPN objects
and action UUIDs, and adds two `WFVPN` setup questions with no text placeholder or
synthetic default identifier. The generic workflow is signed through HubSign;
only generic workflow metadata is sent. Structural checks and signing do **not**
prove that iOS supports the picker during import.

Before enabling the UI/API release, validate on iPhone:
1. Both candidates import successfully and show a VPN picker for the setup questions.
2. Selecting the installed TOLF VPN binds both actions; ON and OFF operate correctly.
3. A profile with optional WebClips launches the exact new names.
If the picker is not supported, stop the release and obtain a native exported
setup template. Do not replace the picker with a string-based VPN parameter.

## Checks and deployment

Run the MobileConfig unit tests, native/public shortcut checks, and main/Quick
Setup UI checks. Rebuild the UK installer after source changes; its embedded
payload must include `tolf_oc_webclips.py` as well as `tolf_oc_mobileconfig.py`.
Deploy these modules together after the iPhone gate passes. Preserve the existing
profile-signing authority and authentication. Deploy the website from the reviewed
branch through the existing GitHub workflow. The optional checkbox defaults off.

Signed candidate snapshots and unsigned sanitized plists are retained under
`shortcuts/public-candidate/`. They contain no VPN credentials or device binding.

Validation completed: 67 AnyConnect backend tests passed across the base and
isolated test environments (the isolated environment supplies the missing
TestClient dependencies). Main AnyConnect UI, Quick AnyConnect, current-device
selection, native/public shortcut checks and JavaScript syntax checks passed.
The UK installer was rebuilt. iPhone import and visual browser QA remain unverified.
