# Native Windows certificate setup

Manual Windows setup creates a personal PPKG on UK. The browser can save it on
any platform, or share the actual file through the native iOS share sheet.
Quick Windows setup also requests `packageFormat: ppkg`, with the existing
current-Windows-device guard. The Windows payload contains neither executables
nor scripts and has no .NET/runtime dependency.

## Authorization

`tolf_windows_ca.py` implements a separate Windows IKEv2 authority, stored at
`/etc/tolf-windows-client-ca` on UK. Device records at
`/var/lib/tolf-api/windows-certificates` contain encrypted private keys. These
directories and records are accessible only to the API service. Production
certificates, keys and personalized packages never go through GitHub Actions.

Each certificate has clientAuth usage and a device UUID in both its subject and
DNS SAN. Its private key is installed into the Windows machine store through
native ClientCertificateInstall, with export disabled. The VPN profile uses
native IKEv2 MachineMethod=Certificate, ForceTunnel and AES256/SHA256/Group14.
This is machine-certificate authentication, rather than password EAP or EAP-TLS.

Riga's restricted `windows-certificate apply|remove UUID NODE MODE` operation
receives only public certificate, public key and CA. `certificate-node.py` uses
the existing routing controller to apply the assignment on Riga or Moscow.
Each connection pins a specific device public key and identity, and uses the
existing routing address pool selected by the owner. No catch-all certificate
connection is installed. Deleting a device removes its authorization and
terminates matching IKE sessions; a failed node operation leaves deletion
pending and packages inaccessible until a retry succeeds. Node certificate
files are not the control plane; issuance and record ownership remain on UK.

Existing password-based devices are migrated only when their owner explicitly
requests a new PPKG. The previous device password and legacy packages are then
revoked. Apple and Android devices use their existing configuration.

## Packaging and deployed paths

The Windows compiler produces a disposable synthetic certificate package:
commit `eb2ebb5876e056b95e87de22260a00200d5b9721`, successful run `37663227444`.
The template PPKG SHA256 is
`b6d307c24d0db8c0ca2bc8abe4cc084072d10ed5c7a73fa26d44f4ed74a689b1`.

`ppkg/personalize.py` replaces the compiler-generated native runtime certificate
blob, password, CA thumbprint, VPN profile name and server. It namespaces package
and runtime-group identities to each device. It preserves the compiler XML
declarations, BOMs and default namespaces and updates the original Microsoft
WIM container with provisioning metadata instead of capturing a new container. Every produced package is extracted again and its
contents compared to the source payload. Only XML and native provisioning XML
are accepted in the template.

UK runtime files:

- `/opt/tolf-api/tolf_windows.py`
- `/opt/tolf-api/tolf_windows_ca.py`
- `/opt/tolf-api/tolf_windows_certificates.py`
- `/opt/tolf-api/tolf_windows_ppkg.py` (deployed copy of `ppkg/personalize.py`)
- `/opt/tolf-api/windows-ppkg-template` (verified extracted Microsoft template)
- `/opt/tolf-api/windows-ppkg-template.ppkg` (original Microsoft-compiled container)
- `/opt/tolf-api/wimtools` (Debian wimtools and its library dependencies)

Riga runtime: `/usr/local/lib/tolf-windows-certificates.py`, invoked through
the certificate dispatch added to `tolf-provision-ssh` and `tolf-provision-root`.
The dispatch is limited to apply/remove, canonical UUIDs, existing nodes and
supported routing modes. CA/private-key files must not be replaced during an
upgrade. Replacing the authority breaks existing installed device certificates.

## Validation and remaining client check

- Microsoft compilation and extracted certificate/VPN payload verification passed.
- 50 Windows tests passed, including certificate identity, encrypted key storage,
  owner isolation, idempotent issuance, deletion failures and invalidated downloads.
- Real restricted apply/remove completed on Riga and Moscow.
- Real API handlers created, served and revoked a personalized PPKG on UK.
- Fourteen quick setup tests passed.

Installation of the personalized package and a VPN handshake from actual Windows
10/11 remain unverified. Native CSP documentation lists Pro, Enterprise and
Education editions; Windows Home is not claimed as supported. Multiple client
certificates installed on one Windows machine also need a selection test.

## Windows installation diagnostic, 8 October 2026

The first Windows client installation returned XML syntax error 0xC00CEE2D.
Version 2.1 personalization preserves compiler XML declarations, encoding BOMs
and namespace spelling, and updates the original WCD container. Two regression
tests cover namespace and escaped-value preservation; 66 Windows/quick tests
pass. A real personalized package passed WIM extraction and payload checks under
the API service user. A Windows retry is still required; these server checks do
not establish that the client error is resolved.

## Local access, PPKG version 2.2

ForceTunnel installs a VPN default route, but Windows retains more-specific
physical-interface routes. Runtime VPNv2 NativeProfile now sets
DisableClassBasedDefaultRoute=true so assigning a 10.x VPN address does not
also install a class-wide 10.0.0.0/8 route. No private address range is blindly
excluded, and certificate authentication and server-side routing are unchanged.

ByPassForLocal is documented as unsupported and is not used. A static PPKG
cannot enumerate live routes, detect an active VNC/RDP peer or synthesize a
route using the correct physical interface/gateway. Local connected subnets
and existing specific physical routes are preserved by Windows routing.
Management reachable only through the default route still needs a specific
physical route; multi-adapter, overlap and remote-control behavior require
client route inspection before a remote-only VPN test.

69 Windows/quick tests passed, including idempotent class-route configuration,
escaping and unchanged authentication/server settings. A real personalized
package was extracted and the runtime routing settings verified on UK under
the API service user. Windows route behavior remains to be checked on client.

References:
- https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/vpn/vpn-routing
- https://learn.microsoft.com/en-us/windows/client-management/mdm/vpnv2-csp

## NativeProfile application error, PPKG version 2.3

Windows client Event 12 returned 0x82AA0002 at VPNv2/profile/NativeProfile.
The compiler runtime had two NativeProfile characteristics and two nested
CryptographySuite characteristics. Version 2.3 converts the complete native
settings into a single VPNv2 ProfileXML string value, avoiding repeated CSP
node creation. The embedded XML follows the documented schema sequence and
uses the IKEv2 protocol spelling. Certificate/CA provisioning still precedes
the VPN group. No executable, script, automatic connection or guessed gateway
is introduced. Existing specific physical routes remain required for remote
management peers that are reached via a default route.

71 Windows/quick tests passed. A personalized package from the actual active
certificate was extracted and checked for one ProfileXML value, one native
profile, one crypto suite, machine certificate authentication, the selected
server and disabled class routes. Windows installation must be retried to
confirm the client error is resolved.

Reference: https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/vpn/vpn-profile-options

## Windows 10 crypto readback, version 2.4

The v2.3 profile installed and appeared in the all-user phonebook with IKEv2
and MachineCertificate. Windows readback showed SHA256128/AES256 for ESP but
DHGroup=None, EncryptionMethod=DES and IntegrityCheckMethod=MD5. The client
reported an incompatible Diffie-Hellman policy and did not connect.

The likely cause is the newer XSD crypto element sequence: PfsGroup appeared
before DHGroup, IntegrityCheckMethod and EncryptionMethod. Version 2.4 uses
the Windows 10 example order: AuthenticationTransformConstants,
CipherTransformConstants, EncryptionMethod, IntegrityCheckMethod, DHGroup,
PfsGroup. Values remain AES256/SHA256/Group14 with no PFS. This is a candidate
client compatibility fix; successful Windows readback and handshake are
required. Windows 11 compatibility with this sequence remains unverified.

Reference: https://directaccess.richardhicks.com/2018/12/10/always-on-vpn-ikev2-security-configuration/

## Confirmed Windows result, 8 October 2026

Version 2.4 did NOT fix the crypto readback. Changing the element order alone
was disproved on the client. The all-user connection still had DHGroup=None,
EncryptionMethod=DES and IntegrityCheckMethod=MD5.

The real connection 05b06800-7ffe-5636-850a-569604c4d7e7 succeeded after an
explicit Set-VpnConnectionIPsecConfiguration and moving obsolete test client
certificates out of LocalMachine/My. Moscow confirmed the matching certificate,
IKEv2 ESTABLISHED and CHILD_SA INSTALLED with AES256/SHA256/MODP2048. This does
not establish that automated PPKG setup is complete.

Windows selected an older certificate when several TOLF certificates were
available. Archiving old certificates is a diagnostic workaround, not a
production per-profile selection mechanism. VPNv2 Certificate/Eku and Issuer
are documented as reserved for future use; do not claim they provide a working
machine certificate filter. EAP-TLS with explicit certificate filtering needs
a separate implementation and client-store validation.

native_candidate.py is an isolated diagnostic builder adapter. It preserves
strict template validation but emits one complete NativeProfile and one
CryptographySuite through native CSP nodes instead of ProfileXML. It is NOT
enabled in the production API. A Windows installation and actual readback of
all six IPsec values must precede enabling it. No executable, script, connection
trigger, local certificate cleanup or guessed physical route is added.

The current-device Moscow authentication fix is also separate from the
general provisioning helper, which remains unchanged. Do not assume newly
created devices inherit the temporary server adjustment.

Reference: https://learn.microsoft.com/en-us/windows/client-management/mdm/vpnv2-csp

## Direct CSP candidate failed

Windows client Event 12 at 12:20:53 returned 0x82AA0002 at VPNv2/TOLF Crypto Check 734b2c87-0b23-4786-a73d-4d7e4e311798/NativeProfile. Consolidating the characteristics did not resolve installation. This candidate is not a working alternative to ProfileXML. Do not deploy it in the API or ask users to remove working connections.

## ProfileXML schema validation, 8 October 2026

The local Windows schemas/VpnProfile/VpnProfileSchema.xsd describes the internal
VpnProfile/VpnConfiguration representation. It is not the input
VPNProfile/NativeProfile schema used by VPNv2 ProfileXML.

A machine-certificate projection of Microsoft's published ProfileXML XSD now
validates generated payloads with lxml. Only the external EAP schema import and
Eap branch are removed; all applicable order, occurrence and type declarations
are preserved. EAP-TLS is not covered by this fixture.

The v2.4 output fails this independent schema check at IntegrityCheckMethod.
The repository generator restores the published order:
AuthenticationTransformConstants, CipherTransformConstants, PfsGroup, DHGroup,
IntegrityCheckMethod, EncryptionMethod. Negative tests also check root, native
and crypto sequence violations.

This is a schema-conformance correction, not a Windows provisioning fix.
The earlier v2.3 output used this order and still produced zero IKE settings.
The runtime API copy and downloadable packages are intentionally unchanged;
the three-parameter installation failure remains unresolved.

## Disposable Windows client readback test

windows-crypto-ci.yml builds a credential-free package from the isolated WCD
container and the repository's strict ProfileXML serializer. It extracts the
result again and compares the runtime bytes. Only one VPN runtime group is
present. No production certificate, key, account or API token is supplied.

A Windows 11 ARM runner compares three paths without connecting a VPN:
VpnClient Add/Set cmdlets, the VPNv2 WMI bridge under SYSTEM, and installation of
the PPKG containing the identical ProfileXML. It records all six actual IPsec
settings and provisioning errors, then removes only its three CI profile names.
The scripts are CI harnesses, not executable commands included in the PPKG and
not a proposed installer for users.

This can separate provider, CSP and PPKG behavior on the hosted Windows client.
A passing result on Windows 11 ARM does not establish Windows 10 x64 behavior
or successful authentication/routing on the user's machine.

## Verified minimal crypto ProfileXML on Windows 11 ARM

Run 37749673807 (commit 2e6e161fc08e63c91def95c603f58cc4171faa4a)
created a SYSTEM/all-user IKEv2 MachineCertificate profile through the escaped
WMI bridge using Servers, NativeProtocolType, the complete CryptographySuite
and Authentication only. Actual native policy readback matched all six fields:
SHA256128, AES256, None (PFS), Group14, SHA256 and AES256.

The original full profile failed, including when its crypto suite was removed.
Each of RememberCredentials, AlwaysOn, RoutingPolicyType and
DisableClassBasedDefaultRoute succeeded individually. Incomplete crypto suites
failed XML parsing. This proves the complete suite is supported on the test OS;
it does not prove the root cause of the full-profile failure or PPKG transport.

The optional-settings sweep exceeded its original three-minute deadline.
Per-case checkpoints and timings now preserve completed evidence. Separate
minimal PPKG variants test one versus two layers of ProfileXML escaping.
No production generator deployment or client connection/reinstallation occurs
as part of these tests. The user’s working profile must be preserved.

Run: https://github.com/sia-tolf/tolf-vpn-web/actions/runs/37749673807

## Verified package candidate — 2026-10-08

Commit 4bf215747f779dd5154931a3c9f305710d141e3f passed Windows ProfileXML
crypto readback run 37754098523 on Windows 11 Enterprise ARM64 build 26200:
https://github.com/sia-tolf/tolf-vpn-web/actions/runs/37754098523

The full PPKG installed through native provisioning. Readback confirmed
MachineCertificate, SHA256128/AES256 for ESP, Group14/SHA256/AES256 for IKE,
PfsGroup None, automatic connection disabled, class-based default routes disabled,
and explicit IPv4 routes 0.0.0.0/1 and 128.0.0.0/1.

The tested Windows provider rejects ForceTunnel combined with
DisableClassBasedDefaultRoute true. SplitTunnel plus the two explicit /1 routes
retains the desired IPv4 Internet routing while allowing more-specific physical
routes to win. This does not automatically protect a remote-management peer
reachable only through a physical default route: that peer needs its existing
specific physical route. IPv6 full-tunnel routing is outside this candidate.

The CI package writer also needed to preserve the compiled UTF-8 BOM.
Without it the credential-free test package failed with C00CEE2D. The production
serializer already preserved that BOM; it was not the production root cause.
Single outer XML attribute escaping was verified; double escaping is a negative
test and correctly fails.

A private preview uses the existing active device
05b06800-7ffe-5636-850a-569604c4d7e7 certificate, with profile display name
'TOLF Test PPKG 05b06800-7ffe-5636-850a-569604c4d7e7' and a separate package ID.
Its PPKG payload round trip and API download checksum were verified. No new
certificate was issued and no server authentication configuration was changed.
Private payloads and bearer URLs are deliberately excluded from Git.
Production runtime/main have not been replaced. Acceptance on the user's
Windows 10 remains pending installation and readback. These tests do not prove
an end-to-end connection on Windows 10.
