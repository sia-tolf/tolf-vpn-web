# Windows IKEv2 PPKG — compiler prototype, 7 October 2026

Manual Windows setup can be prepared from iPad and other platforms.
Quick Windows setup runs only on the current Windows computer.

## Verified result

Windows Configuration Designer 10.0.26100.9457 compiled a genuine WIM-based
PPKG on the GitHub Windows Server 2022 build runner. The successful build:
https://github.com/sia-tolf/tolf-vpn-web/actions/runs/37656724709

Compiler prototype and diagnostics:
https://github.com/sia-tolf/tolf-vpn-web/releases/tag/windows-ppkg-b743b23c23966b762473a034f39b2012e9fb6b8e

The sample contains no production device identity, password, or activation
token. Compilation alone is not successful client installation or connection.
Do not expose this sample as a working TOLF profile on the VPN website.

## Source files

- `profile.py`: full VPNv2 ProfileXML source with AES256/SHA256/Group14.
  This is not a compiled PPKG and is not what the prototype compiler embeds.
- `customization.py`: minimal WCD-native VPN test customization.
  WCD requires separate PackageConfig and Settings XML namespaces and
  ConnectivityProfiles/VPN/VPNSetting/VPNConfig[@VPNProfileName]/VPNSettings.
- `build-prototype.ps1`: installs no components on an end-user computer.
  Runs on the build machine, inspects temporary copies of WCD settings
  stores, and invokes ICD using paths without spaces.
- `.github/workflows/windows-ppkg.yml`: compiler prototype pipeline.
  All published artifacts contain only synthetic test settings.

## Limitations established by the compiler

The shipped Common and Desktop settings stores expose native IKEv2, EAP
configuration, server, routing and credential caching. They do not expose
VPNv2 CryptographySuite or VPN ProfileXML in their VPN setting group.
The generated basic package therefore does NOT include TOLF's required
custom cryptographic policy.

EAP configuration and RememberCredentials do not store the user's RAS
username/password. Never insert a username/password into EapHostConfig
and assume that credentials are installed.

A complete portable package needs a separately verified method to apply
the custom crypto and credentials: for example, a small statically linked
native Win32 provisioning helper executed from the PPKG. This does not
require installing .NET or a separate runtime, but it is executable setup
code inside the package. Its execution identity and per-user credential
scope must be tested before choosing the final implementation.

## Delivery work still required

1. Implement and verify full crypto and credential provisioning.
2. Verify installation and VPN connection on actual Windows 10/11 clients.
   The GitHub compiler runs Windows Server, not Windows 10/11. Home support
   is not established by VPNv2 documentation.
3. Keep per-device issuance, expiry, revocation and all control on UK.
   Do not send real user credentials to public GitHub workflows/releases.
4. Enable .ppkg download and iOS native file sharing only after the package
   works. Reuse a prepared File object in a user-initiated sharing action.

## Primary references

- https://learn.microsoft.com/en-us/windows/configuration/provisioning-packages/provisioning-command-line
- https://learn.microsoft.com/en-us/windows/configuration/provisioning-packages/provisioning-multivariant
- https://learn.microsoft.com/en-us/windows/configuration/wcd/wcd-connectivityprofiles
- https://learn.microsoft.com/en-us/windows/configuration/provisioning-packages/provision-pcs-with-apps
- https://learn.microsoft.com/en-us/windows/win32/api/ras/nf-ras-rassetcredentialsw
- https://learn.microsoft.com/en-us/windows/client-management/mdm/vpnv2-csp
