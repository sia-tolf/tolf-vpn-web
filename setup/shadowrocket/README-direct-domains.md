# Optional direct country domains

The iOS Shadowrocket form offers two independent, initially unchecked options:
Russian domains (ru, su, xn--p1ai, displayed as .рф) and Latvian domains (lv).
The generated domain rules precede FINAL,PROXY. All three Home server choices,
the internal DNS exception and local network rules are preserved.

Preferences contain only country codes and are stored under
tolfShadowrocketDirect:v1:<encoded account id> in this browser's local storage.
An explicitly empty choice is saved. Accounts have independent choices; unavailable
storage falls back to per-page memory. Credentials and generated files are never stored.

GET /client-country is an optional, private/no-store hint. It uses the request
client address and the existing, regularly updated RIPE allocation registry.
It returns RU, LV, or null. Allocation country is approximate and a VPN can
change the visible country. The hint never changes the user's choice or checks
an option, including when it arrives late.

Downloaded files keep their selected rules while travelling. Download a new file
to change rules on a device; there is no automatic country switching.

## Install the optional API hint

Run /opt/tolf-api/venv/bin/python3 setup/shadowrocket/install-direct-country.py
from the checked-out web source. The installer backs up the existing API source,
copies client_country.py to /opt/tolf-api/tolf_client_country.py, and appends
one idempotent registration to main.py. Restart only tolf-api to load it.
VPN node services and existing API routes are not modified.

## Checks

- /opt/tolf-api/venv/bin/python3 tests/shadowrocket-country.py
- node tests/shadowrocket-config.cjs
- node tests/shadowrocket-direct.cjs (jsdom)
- Existing iOS manual-client/setup-mode regressions and tests/shadowrocket-browser.cjs

The browser checks use synthetic credentials, mocked country responses and
downloaded configurations at 320, 390 and 1024 pixels in light and dark themes.
