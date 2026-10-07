# Windows IKEv2 PPKG — prototype, 7 October 2026

Manual Windows setup must allow preparation from iPad and other platforms.
Quick Windows setup runs only on the current Windows computer. Neither the
manual device API nor the manual form may reject iOS User-Agent headers.

`profile.py` generates native VPNv2 ProfileXML for EAP-MSCHAPv2 with the
existing AES256/SHA256/Group14 parameters. Routing mode remains assigned to
the separate Windows identity on the VPN server; it is not an arbitrary
Local ID setting on Windows.

This is a source payload, not a PPKG. Do not rename XML or ZIP to .ppkg.
No working compiler is available on the current Linux control servers.
No PPKG download button is enabled before a real Windows-built package
passes installation and connection checks.

Remaining work:
1. Export and verify the applicable WCD customization schema on Windows,
   including the user scope of the native VPNv2 profile.
2. Compile the payload with Windows Configuration Designer (icd.exe).
3. Verify installed profile, EAP, crypto, routing and connection on Windows
   10/11 Pro. Home support is not established by VPNv2 documentation.
4. Verify credential delivery separately: ProfileXML authentication
   configuration is not RAS username/password storage. The prototype does
   not inject credentials and must not claim password-free initial setup.
5. Connect a Windows build worker to the UK control plane with per-device
   package identity, expiry and revoke checks. Keep control on UK.
6. Only then enable a .ppkg response and native iOS file sharing / Windows
   file saving. File sharing must be initiated by a user gesture and reuse
   a prepared File object so Web Share activation is not lost during fetch.

Existing EXE delivery remains operational until PPKG passes these checks.

Primary references:
- https://learn.microsoft.com/en-us/windows/client-management/mdm/vpnv2-csp
- https://learn.microsoft.com/en-us/windows/configuration/provisioning-packages/provisioning-command-line
- https://learn.microsoft.com/en-us/windows/configuration/provisioning-packages/provisioning-apply-package
