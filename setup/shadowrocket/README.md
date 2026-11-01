# Shadowrocket manual setup

On iOS manual setup, clients appear as Built-in VPN (IKEv2), Cisco Secure Client,
then Shadowrocket (AnyConnect). Android, Windows and quick setup retain their
protocol selection inside the selected mode. Mode tabs always remain available;
a separate quick-setup action validates the selected protocol and physical device.
Protocol choices belong to their platform and mode. Returning to an iOS client
restores that client's fixed protocol. The existing IKEv2 and Cisco controls are
moved, not copied. Browser checks load the actual page and its full script/style
set, using mocked API responses and synthetic credentials only.

Before choosing a mode, quick setup is highlighted as the recommended action;
no panel opens until the user selects a mode. Manual selection moves the highlight
to the manual tab. A short translated instruction precedes the three iOS clients.

On wide screens (700px and above), Cisco and Shadowrocket installation controls
share one row: the installation button takes the left half and its confirmation
checkbox is centered in the right half. Narrow screens retain stacked controls
with the installation button filling the full content width. Password fields
also fill the content width and use an accessible eye control inside the field
to show or hide the password; no separate text button takes field width.

## Control design

The design reference is Smart DNS, repository `sia-tolf/tolf-dns-web`, commit
`9c37c8c614e05b6e52e8fea65820728fb58bb413`. Reuse the existing shared TOLF
button stylesheet and its tokens. Do not introduce a VPN-specific palette.
The iOS / Android / Windows control retains the original unified three-part
switcher from `css/styles.css`, including on narrow screens. Do not replace it
with separate platform buttons. Mode choices use the Smart DNS outlined and
selected states; actions are 48px with the same borders, radii and typography.
All setup buttons retain their approved action colors in both availability
states. Disabled primary actions use the same blue and white label, including
quick setup, Shadowrocket, Cisco and Windows actions. The shared disabled tokens
are mapped within `#quickSetupCard`; do not add per-button palette exceptions.
`disabled`, `aria-disabled` and existing validation still block unavailable actions.
Browser checks compare computed colors and geometry directly with the checked-out
Smart DNS page in light and dark themes. For local browser checks, put that exact
reference checkout in `.smartdns-reference/`; CI prepares it automatically.
The preview artifact also contains an inventory of every setup button in its
current and temporarily disabled state across quick setup, iOS clients,
Shadowrocket account/settings/file screens, Android and Windows. Review the
`unapproved` entries in these JSON inventories before publication.

Shadowrocket uses the same website username and password. Passkey-only users add
credentials to their existing account. `createOnly: true` prevents a concurrent
password creation from becoming an accidental reset. `/password/verify` checks
only the authenticated account and leaves credentials and sessions unchanged.
The verification shares login rate limits and rechecks the session after hashing.

Configuration and optional sign-in text files are assembled locally. Passwords
are kept only in the current page and cleared on account changes or pagehide.
The server never stores generated files or plaintext passwords. Three tested
OpenConnect endpoints use own DNS 10.254.0.53 and the built-in PROXY policy so
Home controls the selected server. New York uses the Moscow relay.

The tested unquoted node syntax is used without guessing password escaping.
For separators, quotes or whitespace, the user explicitly chooses a file without
passwords and supplies the password in each server after import. Generated
24-character passwords use the URL-safe alphabet and support complete import.

## Deploy

Run tests before deployment. Install the additive API changes before publishing
the frontend. `install-api.py --check` reads only the target module and validates
the reviewed live checksum. `--apply` backs up that one code file and changes
only capabilities/set-password functions plus the new verify handler. It retains
other live API logic, compiles the candidate, restarts only `tolf-api.service`,
checks public capabilities and restores the previous module if health fails.
It does not alter account records, VPN services, traps, guards or watchdogs.

The exact baseline checksum is intentional. If it changes, review current API
code and prepare another patch rather than overriding this drift check.

Checks: `node tests/shadowrocket-config.cjs`, `node tests/ios-manual-clients.cjs`,
`node tests/manual-entry.cjs`, `node tests/cisco-client-install.cjs`,
`python tests/password-auth/test_password_auth.py`, and browser checks in
`tests/shadowrocket-browser.cjs`. The browser workflow covers RU/LV/EN at
320/390/1024px and real local file downloads, using synthetic credentials only.
