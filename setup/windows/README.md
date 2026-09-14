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


## Native setup 2.1 — optional IPv4 exclusions

The first step loads the device configuration and its saved local preferences.
The user can then enter up to 32 IPv4 CIDR networks, one per line (commas and
semicolons also work). The empty default preserves the existing full tunnel.
The installer validates prefixes, rejects host bits and exclusion of all IPv4,
and normalizes duplicate/overlapping networks. IPv6 exclusions are not supported.

“Save without connecting” configures a disconnected profile without dialing it.
“Save and connect” performs the same save and then opens the Windows dial dialog.
A connected/connecting profile must be disconnected before its routes can change.
Nothing auto-populates an RDP subnet or infers a subnet from a partial IP address.

For a nonempty exclusion list, native RAS sets only the IPv4 default-gateway
option to split routing and WMI adds the complement of the excluded IPv4 networks
through `PS_VpnConnectionRoute`. Independent IPv6 profile settings are preserved;
this feature does not add IPv6 tunneling to a profile that did not already use it.
Windows activates these profile routes on connection and removes them on
disconnection, including connections made after the installer exits. No global
physical-interface route, scheduled task or background service is installed.
Excluded destinations follow the computer's existing routing table; ordinary
longest-prefix route selection still applies, including existing local routes.
The installer does not configure server routes or remote gateways. An RDP return
path may use a different source network from the VM's destination subnet, so an
exclusion list by itself cannot guarantee RDP reachability.

The canonical list is stored for the current Windows user under
`HKCU\Software\TOLF\VPN\<device UUID>\ExcludedIPv4`. It is reloaded when the user
opens a valid setup link for the same device. Clearing and saving the list removes
the managed profile routes and restores full tunneling. Failed route changes are
rolled back; rollback failure is surfaced and connection is not started. These
are process-level rollback guarantees, not recovery from a power failure midway
through a change. VPN credentials and policy retain the 2.0 update behavior.

Tests cover strict CIDR parsing, IPv4 partition coverage, boundary addresses,
normalization, real Windows provider route creation/removal, repeated setup,
failed updates and removal of a newly created profile after a route failure.
Tests do not dial a VPN. End-to-end RDP and live connection testing remain separate.

The London updater accepts the verified previous native module and performs a
backup and health check. Publishing the repository does not update the EXE served
by London: execute the release's updater there, then download the new installer.

- https://learn.microsoft.com/en-us/previous-versions/windows/desktop/vpnclientpsprov/add-ps-vpnconnectionroute
- https://learn.microsoft.com/en-us/previous-versions/windows/desktop/vpnclientpsprov/remove-ps-vpnconnectionroute


## Native setup and controller 2.3

The installer creates per-user Desktop and Start Menu shortcuts: **TOLF VPN**
opens settings; **TOLF VPN Widget** opens a compact native Win32 control panel.
The versioned application lives in `%LOCALAPPDATA%/TOLF/VPN/2.3.0` and no longer
needs a setup token for everyday use. It discovers matching existing per-user
TOLF Riga IKEv2/EAP26 profiles. Other VPN profiles are excluded.

Connect uses native RAS and credentials already stored by Windows. Only a
confirmed RAS connected state closes the setup window; failure leaves it open.
The controller remains available in the notification area after successful setup.
The widget can connect/disconnect the selected profile, open settings, and be
pinned above other windows. Closing its window hides it to the tray; Exit closes
the controller without disconnecting an established VPN. Launch at Windows sign-in
is optional, off by default, and implemented as a per-user Startup shortcut.

Settings show the actual profile server, IKEv2 protocol and assigned DNS when the
interface is available. DNS and server selection remain server-managed. Saved
IPv4 exclusions can be edited while disconnected without fetching a link or
rewriting credentials. Unsaved edits disable profile switching and dialing.
A one-second RAS status poll observes connections changed outside the controller.
No global routes, service, scheduled task, WebView or external runtime is installed.

Native integration tests include settings-only route updates preserving stored
credentials and refusing to recreate a deleted profile. Live VPN dialing and
Windows 10/11 visual checks still require an interactive Windows environment.
