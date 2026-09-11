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

## GUI setup 1.1 (test build)

`desktop/TolfSetup.cs` is a .NET Framework Windows Forms application, compiled on
Windows by `build-desktop.ps1`. It receives the personal link from the download
filename or a pasted link, POSTs to the fixed HTTPS API, and configures native
IKEv2 through its embedded PowerShell resource. Credentials travel over stdin,
not command-line arguments or temporary files. No browser security settings,
certificate validation, or machine-wide execution policy are disabled.
After configuration it invokes rasdial with only the saved connection name.

The executable is shared across users; the token in the filename expires with
the personal link. Renaming the file requires pasting the original link. The
signed-in device creation and Apple/Android API remain unchanged. Older ZIP
packages remain internal to the API so previously issued links keep working;
they are no longer offered as downloads. Server-side storage retention remains
48 hours, download links 24 hours. Links can be reused during that period.

The workflow publishes an **unsigned prerelease**, plus a self-contained London
updater with backups, a v1 source-hash guard and health-check rollback. Production
code signing and real Windows VPN connection testing remain required. Neither
compilation nor API tests prove native Windows EAP/DNS behavior.
