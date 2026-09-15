# Windows 2.6.1 profile labels

Native source restored from the actual 2.6.0 release commit
4d554880347a6b78bd2644cfd32f3daca103b91a, retaining its controller,
widget, saved EAP identity handling, password updates and per-device exclusions.

This API extends the deployed routing-compatible 2.6 API. The existing settings
contract stays exactly four fields unless the caller requests `?labels=true`.
Opted-in callers also receive `displayName` and `routingMode` from the active
device record. Existing unexpired setup links work without reissuing credentials.
The native client stores these non-secret labels per device under HKCU and uses
one caption in the settings window and widget. RAS names/UUIDs are unchanged.
Empty Moscow routing mode is shown as AUTO; old profiles lacking metadata retain
the location/short-ID caption until their setup link is loaded and saved again.

Deploy only the matching release's update-windows-gui.py on London EDISUK.
The updater accepts the exact deployed routing API hash or its own payload,
backs up affected files, and verifies routing/password/labels capabilities.
It does not modify Riga/Moscow configuration or the account/device database.

On Windows, disconnect the profile being updated, exit the old widget via its
tray menu, download the new installer through the existing device setup page,
load settings and Save without connecting. Saved network exclusions are loaded
and preserved. Repeat for each old profile to acquire its name/mode metadata.
No device deletion or new device creation is required.
