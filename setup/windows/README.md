# Windows support — initial Riga rollout

The public web UI exposes Windows only after GET /windows/capabilities reports API v1.0.
Selecting the platform only reads device state. Creating a device requires an explicit form submission.

Run setup/install-windows-api.py as root on the London API node after reviewing it.
It snapshots main.py and SQLite, adds an isolated device table, and hooks account deletion.
On a failed health check it restores the API source files (not the database snapshot).
Existing iOS/Android endpoints and shared credentials are retained.

Server prerequisite: Riga riga-windows IKEv2/EAP-MSCHAPv2 connection, AES256/SHA256/Group14,
ESP AES256/SHA256 without PFS, and vpn-pool-riga-sr.
Windows connections currently use Riga only. Moscow entry and custom DNS/Local ID controls
are not exposed for Windows. DNS is assigned by the existing server pool.

Each device uses a distinct UUID provisioned via the existing Riga SSH service.
The authenticated account owns that UUID. API SQLite stores no VPN passwords.
Temporary ZIP files contain credentials, have mode 0600, expire after 24h and use
existing profile cleanup after 48h. Device deletion invalidates its package links.
Credential deletion prevents subsequent authentication; it does not forcibly terminate an existing IKE SA.

Install-TOLF.cmd invokes Windows PowerShell with process-only ExecutionPolicy Bypass.
No machine-wide execution policy is changed. The per-user IKEv2 entry uses EAP26,
explicit IPsec parameters and RasSetCredentialsW to persist the credentials in Windows.
It does not connect automatically. The downloaded ZIP and extracted files contain
credentials and should be removed after successful installation.

Validation:
  python -m pytest tests/windows/test_devices.py tests/windows/test_installer.py
  node tests/windows/frontend.cjs
  node tests/measurement-regression.cjs

Tests require FastAPI, httpx and pytest and use an isolated SQLite database with
mock VPN provisioning; they never provision a real VPN account.
Native Windows installation, EAP authentication, DNS and route behavior require
an end-to-end test on the user's Windows computer before calling the rollout verified.

References:
- https://docs.strongswan.org/docs/latest/interop/windowsClients.html
- https://learn.microsoft.com/en-us/powershell/module/vpnclient/set-vpnconnectionipsecconfiguration
- https://learn.microsoft.com/en-us/windows/win32/api/ras/nf-ras-rassetcredentialsw

## Native setup 2.0 (test build)

The downloadable EXE is native C++17, built with MSVC `/MT` for Windows 10/11
x64 (Windows 10 version 1607 or newer). It requires no .NET Framework,
PowerShell process, Python, Node.js or separately installed Visual C++ runtime.
The C++ runtime is linked into the executable. Only built-in Windows DLLs are
imported. PowerShell and MSVC are used on the build runner, not the user's PC.

WinHTTP retrieves settings from the fixed HTTPS API with TLS certificate checks,
redirects disabled, a bounded response, and timeouts. A strict flat JSON parser
validates the endpoint, device UUID and matching username. Personal tokens are
accepted only from the exact API link or the established download filename.
Credentials never appear in command lines, logs or temporary files.

Native COM calls the inbox Windows VPN WMI provider directly. `PS_VpnConnection`
creates a per-user IKEv2 EAP-MSCHAPv2 profile, with Windows full tunneling and
server-side `sr` routing. `PS_VpnConnectionIPsecConfiguration.SetByCustomPolicy`
sets AES256/SHA256/DH14, SHA256128/AES256 ESP and no PFS. RAS stores credentials;
`RasDialDlgW` supplies Windows' connection progress and Cancel button. The
connection remains available in Windows Settings after the installer closes.
No new background agent, service, root certificate or firewall rule is installed.

Preflight checks the native VPN provider and required services before fetching
credentials. Reruns reuse the matching entry, reject conflicting entries, and
remove a newly created entry when configuration fails. Existing matching entries
are retained on failure; policy/credential updates are not a full transaction.
The UI supports English, Russian and Latvian and runs as the current user.

Windows CI builds and checks DLL dependencies; its native integration executable
validates links/JSON, creates a temporary profile with dummy credentials, sets
IPsec policy, repeats setup, rejects conflicts and tests rollback, then removes
the temporary connection. Tests do not dial a real VPN or use customer credentials.
The build is unsigned. Real Windows 10/11 client connection, DNS, routing and UI
checks remain required before a production release.

The release also contains a London updater with verified payload hashes, backups,
a known-source guard for 1.0/1.1/1.2 and health-check rollback. The live API's
installerVersion changes only after that updater is executed on London. Previous
personal links remain valid until expiry; retained ZIP internals support existing
API storage and are not the downloadable native EXE.

Native interfaces are documented by Microsoft:
- https://learn.microsoft.com/en-us/previous-versions/windows/desktop/vpnclientpsprov/add-ps-vpnconnection
- https://learn.microsoft.com/en-us/previous-versions/windows/desktop/vpnclientpsprov/setbycustompolicy-ps-vpnconnectionipsecconfiguration
- https://learn.microsoft.com/en-us/windows/win32/api/ras/nf-ras-rassetcredentialsw
- https://learn.microsoft.com/en-us/windows/win32/api/rasdlg/nf-rasdlg-rasdialdlgw
