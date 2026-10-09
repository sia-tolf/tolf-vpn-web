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
Each connection requires the pinned Windows CA and exact device identity, and uses the
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

## Windows 10 readback correction — 2026-10-08

The user's Windows 10 installed the full SplitTunnel candidate but retained only
SHA256128/AES256 for ESP; DHGroup/EncryptionMethod/IntegrityCheckMethod stayed
None/DES/MD5. Windows 11 success was insufficient to accept this candidate.

A controlled separate preview changed only one cryptography field: it omitted
the optional PfsGroup=None element. Windows 10 readback then confirmed
SHA256128, AES256, Group14, AES256, SHA256, and PfsGroup None without a manual
Set-VpnConnectionIPsecConfiguration step. This demonstrates that explicit
PfsGroup=None interrupted later crypto application on this tested Windows 10.
The generator now omits that field while retaining the validated template
restriction PfsGroup=None. Machine certificate authentication and two /1 IPv4
routes are unchanged. The user subsequently confirmed successful connection and working traffic
with the NoPFS preview after isolating its existing certificate. No login or
password was added. This is end-to-end acceptance on this Windows 10 machine,
not acceptance of multiple certificates or a universal Windows package.


## Certificate selection follow-up and Windows 11 regression — 2026-10-08

During the NoPFS connection attempt, Moscow logged the obsolete device
3766f7b0-7e99-530b-8149-83e730ae6760 certificate instead of the active
05b06800-7ffe-5636-850a-569604c4d7e7 certificate. The user confirmed both
certificates were in LocalMachine/My with private keys. Moving the obsolete
certificate to the existing archive left only the active certificate in My;
the next attempt connected. The cause of the obsolete certificate returning
is not established. Inventory retained provisioning packages before proposing
removal; preserve the working profile, package and certificate. Do not treat
profile deletion as proof that its provisioning package has been removed.

Windows 11 ARM run 37756192604 for commit 87bbed7 failed. The native Add/Set
baseline matched all six crypto values, but the generated full ProfileXML CSP
case failed and the full PPKG profile was absent on readback. Provisioning
reported 0x800705B9 at VPNv2/TOLF-CI-PPKG. Therefore omitting PfsGroup is
confirmed on the user's Windows 10 only; this generator must not be deployed
as a universal Windows 10/11 solution. Preserve the failing check and investigate
OS-specific validation rather than weakening the success criteria.

Run: https://github.com/sia-tolf/tolf-vpn-web/actions/runs/37756192604

MachineCertificateEKUFilter is a VpnClient cmdlet option. VPNv2's native
Certificate/Eku and Issuer nodes are documented as reserved for future use;
no supported pure-ProfileXML per-device filter has been demonstrated. Do not
issue new device certificates or change the working authentication based only
on the existence of these nodes. Certificate-only authentication remains the
requirement.

## Controlled PFS matrix - 2026-10-09

Run 37883393931 at commit 2bb5fdc tested three otherwise identical payloads on separate Windows 11 Enterprise ARM64 build 26200 runners.
https://github.com/sia-tolf/tolf-vpn-web/actions/runs/37883393931

| PfsGroup XML | Full CSP | Full PPKG |
| --- | --- | --- |
| omitted | failed | failed, profile absent |
| None | passed | passed, six policy fields matched |
| PFS2048 | passed | passed, six policy fields matched |

Both passing packages retained MachineCertificate, disabled automatic connection and class-based routes, and installed both IPv4 /1 routes. Windows 10 remains accepted only for the NoPFS preview with a single active certificate. PFS2048 installation and actual handshake/rekey on Windows 10 remain unverified. The server ESP proposal lacks a DH group; assess rekey compatibility before a PFS2048 connection test. Do not deploy either candidate universally.

The user confirmed another successful connection after package cleanup on 9 October. Inventory IsInstalled=False did not establish absence of VPN profiles or certificates. Multi-certificate selection remains unresolved. Certificate-only authentication remains required.

The user explicitly authorized the private preview and repository publication on 9 October. A PFS2048 installation-only preview was built with the existing certificate/key, separate package and profile identities, and no server provisioning call. Extracted runtime bytes and the HTTPS download checksum matched. Private bearer URLs and sensitive payloads remain excluded from Git. Windows 10 readback remains pending; production configuration is unchanged.

## Windows 10 PFS2048 acceptance - 2026-10-09

The user installed the separate PFS2048 preview and confirmed native readback
of SHA256128/AES256, Group14/AES256/SHA256 and PFS2048 without a manual policy
repair. The connection succeeded using the existing device certificate.

The isolated Moscow device ESP policy now accepts aes256-sha256-modp2048-none,
retaining NoPFS compatibility. All 17 connections loaded with zero unloaded.
Server SA readback confirmed the intended certificate, IKE ESTABLISHED,
CHILD_SA INSTALLED, AES256/SHA256 and traffic in both directions. A targeted
CHILD_SA rekey succeeded and installed a replacement SA with MODP_2048 while
the IKE SA remained established. This verifies PFS beyond initial IKE_AUTH.

The repository generator now emits explicit PFS2048 in the published XSD
sequence, while keeping the compiled template's None validation separate.
CI defaults to testing the unmodified generator output; explicit None and
omitted-field diagnostics remain available in the package builder. Server
provisioning source accepts optional MODP2048 for ESP. Deployment remains
pending; the generic server certificate constraint and multi-certificate
selection issues are separate and are not claimed resolved.

## CA-chain authentication correction - 2026-10-09

A fresh Windows 10 connection with the PFS2048 profile failed when raw public-key
and CA constraints were mixed. A leaf-certificate-plus-CA candidate also failed
while the previous raw public key remained loaded. Logs showed successful RSA
signature verification, followed by a failed CA constraint.

Moving only this device's raw public key and leaf certificate out of the
auto-loaded credential directories and clearing/reloading credentials resolved
the conflict. The per-device connection now requires the pinned CA and exact
CN, without a raw-key or independently trusted leaf constraint. Existing IKE
session 1564 survived credential reload. The user's next reconnect created
session 1565; Moscow explicitly logged the trusted TOLF Windows IKEv2 Device CA,
a completed root chain, RSA authentication success and installed CHILD_SA 1420.
Traffic flowed in both directions. No username or password was added.

The restricted provisioning helper now stores public audit material under
/etc/swanctl/tolf-certificates, outside x509 and pubkey auto-load directories.
Before modifying configuration it validates the pinned CA, signed leaf, exact
device CN and equality of the supplied public key to the leaf's public key.
Legacy imported trust files cause an explicit failure rather than silently
retaining conflicting credential state. Existing legacy devices require an
operator migration and one credential reload; no daemon restart is needed.

Five isolated node-operation tests exercise real OpenSSL verification, retry,
wrong-key rejection, wrong-device rejection, CA replacement rejection and the
legacy migration guard. All 67 Windows Python tests pass. Windows 11 generator
readback run 37886411707 also passed both SYSTEM and elevated package checks.
https://github.com/sia-tolf/tolf-vpn-web/actions/runs/37886411707

Multiple installed machine certificates remain a separate unresolved client
selection issue. Do not represent this server correction as a per-profile
Windows certificate selector. Production generator rollout is still pending.

## Runtime rollout - 2026-10-09

The corrected restricted helper was deployed on Riga with a preserved backup.
A real restricted apply for the existing Moscow device succeeded. The final
SA inventory no longer showed that device; the cause is not established and
a post-rollout client reconnect remains required. Both nodes have no legacy TOLF leaf/raw-key trust imports
in their auto-load directories. Public audit records remain outside those dirs.

The verified ProfileXML generator was deployed on UK as PPKG version 2.5. The
package metadata version was incremented from 2.4; payload crypto and routing
match the accepted PFS2048 candidate. Before deployment, building with the
existing certificate under the API service account and extracting the result
confirmed version 2.5, MachineCertificate, Group14/PFS2048 and both /1 routes.
After the atomic module update and API restart, certificatePackages health was
true. Source SHA256: d696fbead33d36a3312663d35cf5814e76f23225c8170436c9e9a24d69bd7f65.

The user's installed working profile is unchanged and does not need reinstall.
Previously saved packages are not rewritten. Multiple machine certificates
remain an unresolved client-selection limitation; deleting VPN profiles alone
does not remove their certificates.

## Post-rollout acceptance - 2026-10-09

The user's reconnect after the restricted helper and generator rollout created
IKE session 1568 and installed CHILD_SA 1424. Moscow's 05:26:58 UTC log explicitly
recorded the intended 05b068 device certificate, trusted TOLF Windows IKEv2
Device CA and successful RSA authentication. SA readback showed AES256/SHA256,
MODP2048 for IKE, virtual address 10.10.10.14, and traffic in both directions.
This closes the post-rollout reconnect gate above. It does not resolve multiple
installed client certificates.

## Isolated certificate-selection feasibility gate - 2026-10-09

VPNv2 MachineCertificate Certificate/Eku and Certificate/Issuer remain documented
as reserved for future use. A VpnClient cmdlet filter is not proof of pure-PPKG
support. EAP-TLS has documented CA and custom-EKU certificate filters and remains
certificate-only (EAP type 13, not password type 26).

The new isolated CI builder substitutes EAP-TLS in the accepted crypto/routing
payload, with automatic certificate selection, mandatory server CA/name
validation, client CA filtering, a distinct UUID-derived custom EKU per test
profile, and disabled all-purpose/any-purpose certificate fallback. It contains
no client certificate, private key, password or live server target. WIM extraction
roundtrip passed on UK. The Windows CI gate compares two distinct native EAP
configurations and one full PPKG readback, including all six crypto settings.

This is a feasibility test, not deployed authentication or connection acceptance.
Production issuance and installed profiles are unchanged. The existing gateway
does not have eap-tls loaded; server support, user-certificate provisioning,
per-device authorization/revocation, Windows 10 readback and real selection with
two installed certificates must be verified before any production conversion.

References:
- https://learn.microsoft.com/en-us/windows/client-management/mdm/vpnv2-csp
- https://learn.microsoft.com/en-us/windows/client-management/mdm/eap-configuration
- https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gpwl/65562521-4153-4e20-9c4a-612e190886ee
- https://docs.strongswan.org/docs/6.0/interop/windowsUserServerConf.html

## EAP-TLS filter transport verified on Windows 11 - 2026-10-09

Run 37890724944 at e49ed6eedba71d07c3079f1622f7f01def979e50 passed both
package and Windows 11 ARM readback jobs:
https://github.com/sia-tolf/tolf-vpn-web/actions/runs/37890724944

Two distinct native VPN entries retained their distinct custom EKU OIDs and
enabled client-CA/client-auth filters. Full native PPKG installation retained
EAP type 13, server CA/name validation, automatic certificate selection,
client CA/custom EKU filtering, and all six accepted IPsec policy values,
including Group14 and PFS2048.

Earlier runs failed strict text comparison because Windows formats hash bytes
with spaces and omits disabled optional fields. Raw readback confirmed the
required filters were present. Hash comparisons now preserve exact bytes;
only the documented false defaults for omitted AllPurposeEnabled and disabled
AnyPurposeEKUList are treated as false. No enabled CA or client-auth filter may
be omitted. Reference:
https://learn.microsoft.com/en-us/windows/win32/eaphost/eaptlsconnectionpropertiesv3schema-filterinfoparams-complextype

No certificate was installed and no connection was attempted in this CI gate.
Thus this proves transport/readback, not actual multi-certificate selection,
Windows 10 support, native user-certificate installation, or gateway EAP-TLS
authentication. Production remains on the accepted MachineCertificate profile.

## Native user-certificate PPKG gate - 2026-10-09

Run 37891791610 passed package generation, EAP filter/crypto readback and
native certificate-store provisioning on Windows 11 ARM:
https://github.com/sia-tolf/tolf-vpn-web/actions/runs/37891791610

Two synthetic User-scoped PFX credentials installed in CurrentUser/My, both
with private keys, both absent from LocalMachine/My, and each preserving its
distinct custom EKU. The Device-scoped control installed only in LocalMachine/My.
These are disposable CI credentials, not production credentials.

The preceding run 37891423900 successfully installed both scopes but returned
an empty custom EKU OID value for the large 2.25 UUID-integer subidentifier in
both stores. Changing synthetic identifiers to bounded 16-bit arcs under the
documentation-only enterprise arc 1.3.6.1.4.1.32473 resolved readback. Both
certificate and EAP profile tests now use this bounded format. Do not use that
documentation enterprise arc for production issuance; an appropriate owned
namespace is a remaining design gate. This test establishes observed decoding
behavior, not a universal Windows OID limit.

No connection was attempted. Windows 10 acceptance, actual certificate selection
with two credentials, gateway EAP-TLS authorization/revocation and interactive
PPKG installation context remain unverified. Current production MachineCertificate
profiles, certificates, generator and gateway configuration were not changed.

## Windows 10 EAP-TLS A/B candidate staged - 2026-10-09

The acceptance builder creates two seven-day user-certificate PPKGs under a
private UK directory. Signing material stays on UK. Packages use a temporary
dedicated CA, two different client certificates and bounded documentation-only
custom EKU values (temporary test only). Each profile pins the Riga server name
and ISRG Root X1, enables client-CA/custom-EKU filtering, and includes only a
10.250.80.1/32 split route. Both certificate chains and four-provider WIM
roundtrips passed. Package keys and blobs are not committed.

Riga already had eap-tls loaded. Two narrow EAP_TLS connections and one-address
pools were loaded (10 connections, 0 unloaded; 6 pools, 0 unloaded). The
temporary CA was confirmed loaded. Test identities have distinct exact EAP IDs;
actual TLS certificate identity/authorization binding remains an acceptance
gate. The test address 10.250.80.1/32 is assigned to loopback temporarily.
Existing connections and gateway credentials were not replaced; no daemon
restart occurred.

Delivery is blocked pending explicit credential-file transfer approval.
Automatic review rejected public HTTPS publication of private-key-bearing
packages, and also rejected extracting a chunk for private transfer as
unauthorized credential disclosure. No public route or copy was created.
Use authenticated private delivery after approval; do not retry public serving.
No Windows installation or connection has yet been attempted.

## Authenticated candidate delivery - 2026-10-09

The user explicitly approved receiving both private-key-bearing test packages
and requested Windows download links. Automatic review still rejected
unauthenticated URL serving. A materially safer delivery path was then accepted:
two exact HTTPS paths protected by independent temporary HTTP Basic credentials.
Caddy stores only a password hash, serving files are root-owned/caddy-readable,
and the UK signing directory remains private. Both URLs return 401 without
credentials and 200 with credentials; response bytes match the private originals.
No URLs, download credentials, client private keys or PFX blobs are committed.
Windows installation/selection/connection acceptance remains pending.


### Moscow A/B acceptance staging — 2026-10-09

Riga attempt reached the server via Moscow, but the generic dispatcher offered EAP-MSCHAPv2 after the client sent its certificate UPN. No client EAP-TLS exchange occurred. Server key loading was also repaired separately. These failures were not covered by build/installation CI.

Moscow eap-tls 6.0.3-r2 installed; authorized swanctl service restart completed and plugin readback confirmed. Temporary Moscow A/B PPKGs target ikev2.tolf.is, pin ISRG Root X1 and distinct client CA/custom EKU filters. Private CA/key/PFX remain under the UK private acceptance directory; only public CA was sent to Moscow.

Server test policy is restricted to this VM's initial IKE identity 192.168.200.213, EAP-TLS and the separate seven-day Moscow CA. This is a temporary dispatch workaround for the acceptance test, not a production selection design. Pool 10.250.81.11–12; only CHILD selector 10.250.81.1/32. Runtime loopback address and narrowly scoped ICMP input rule added. No extra daemon restart needed to load the test configuration.

PPKG four-provider WIM roundtrip and both client sslclient chains verified. HTTPS anonymous requests returned 401; authenticated downloads returned 200 and exact package bytes. Runtime connection readback shows EAP_TLS and the temporary CA. Windows 10 installation, handshake, correct A/B certificate selection and ping remain UNVERIFIED until the user's live attempts and server logs.

Cleanup: remove /etc/swanctl/conf.d/tolf-eaptls-moscow-test-20261009.conf and its public CA, reload normal credentials/connections/pools, remove test loopback and labeled nft ICMP rule, and remove authenticated download routes/files after acceptance. Do not remove production certificates or profiles.

Moscow first live attempt 2026-10-09 07:56:25 UTC: actual Windows IKE ID was 192.168.8.109, not the earlier VM IP. The client sent the expected A UPN; generic dispatch selected MSCHAPv2 and client replied EAP_NAK. Corrected temporary remote ID to the observed value and reloaded connections (18 loaded, 0 unloaded), without restart. TLS exchange and certificate selection still await retry. Anonymous HTTPS A/B rechecked: both 401.

Live Windows acceptance 2026-10-09: A at 08:07:25–27 UTC sent TLS client CN=tolf-eap-test-a-cfe2a91a187a@tolf.is, verified temporary CA, EAP_TLS success, IKE/CHILD established, VIP 10.250.81.11. B at 08:08:33 UTC sent distinct TLS client CN=tolf-eap-test-b-432b7001527b@tolf.is, verified the same temporary CA, EAP_TLS success, IKE/CHILD established, VIP 10.250.81.12. User reported successful ping for both. A disconnected before B. Both installed profiles therefore selected their intended certificates in this live sequence. Reboot/reinstallation, missing/mismatched certificate negative tests, and production dispatch independent of changing IKE IP remain pending.

### Moscow EAP dynamic stage — 2026-10-09 08:19 UTC

After live A and B acceptance, installed strongswan-mod-eap-dynamic 6.0.3-r2
without restarting charon. Runtime stats still exclude eap-dynamic.
Prepared root-only /root/tolf-eaptls-dynamic-stage-20261009 on Moscow:
- managed.candidate changes only the generic dispatcher from eap-mschapv2 to
  eap-dynamic; keeps its deliberately unsatisfied group authorization constraint.
- plugin.candidate enables peer negotiation with preferred TLS and MSCHAPv2.
- test.candidate replaces the source-IP-specific test policy with exact A and B
  EAP identities, each constrained to the temporary test CA and ping-only subnet.
- activate.sh checks the active configuration still matches the backups,
  restarts swanctl, checks plugin and both policies, and restores backups on
  those checks failing. Shell syntax was checked; activation has not been run.

Activation disconnects current SAs and requires a coordinated restart.
Live checks must establish both test identities through the dispatcher, show
their own certificate in the logs, and verify existing password clients recover.
The managed dispatcher modification is temporary: the routing controller can
overwrite it on a routing update. Integrate the controller only after acceptance.
Production issuance/generator is unchanged. Temporary custom EKU namespace must
not be promoted to production; certificate selection and per-device authorization
still require a production design and negative acceptance tests.

### Moscow EAP dynamic activated — 2026-10-09 09:24:34 UTC

User explicitly approved the restart. Activation checked all three active files
against staged backups and restarted swanctl. A bounded startup readiness check
was added before verifying the loaded plugin and policies.
Runtime confirms eap-dynamic and eap-tls loaded; both identity-a and identity-b
policies have remote id %any, exact EAP identity, the temporary client CA,
and only 10.250.81.1/32 traffic selectors. The source-IP-specific policy is removed.
Existing ikev2-yt password session recovered with IKE and CHILD established.
A/B Windows reconnection and ping after this change are still pending.
Production generator remains unchanged; temporary dispatcher update is not
yet persistent across routing-controller rewrites.

### Post-restart A acceptance — 2026-10-09 09:30:03–04 UTC

Windows user confirmed A connected and ping passed. Moscow logs confirm TLS
peer certificate CN=tolf-eap-test-a-cfe2a91a187a@tolf.is, trusted temporary
Moscow test CA, EAP_TLS success, IKE and CHILD established under
tolf-eaptls-moscow-identity-a. VIP 10.250.81.11; four packets in and out.
The configured remote id is %any, so no source-IP constraint remains.
Initial peer selection directly chose identity-a; this run does not prove
negotiation through tolf-win-dispatch or switching to identity-b. B is pending.

### Post-restart B acceptance — 2026-10-09 09:36:12–13 UTC

Windows user confirmed B connected and ping passed. Initial selection chose
identity-a, then the received B EAP identity failed the A identity constraint
and charon switched to identity-b before TLS authentication.
TLS peer certificate CN=tolf-eap-test-b-432b7001527b@tolf.is was verified against
the temporary Moscow CA; EAP_TLS succeeded and IKE/CHILD established.
VIP 10.250.81.12; four packets in and out. Thus both installed certificates
selected their respective profiles without a configured client-IP constraint.
This proves A-to-B peer-policy switching; it does not exercise generic dynamic
dispatcher negotiation. Only the ping subnet was tested, not Internet routing.

### B Internet server-side preparation — 2026-10-09

After user requested continuing with Internet routing, changed only identity-b
to existing vpn-pool (10.10.10.0/24, DNS 10.254.0.53) and local_ts 0.0.0.0/0.
A remains ping-only. Full standard configuration reload succeeded: 19 loaded,
0 unloaded; no daemon restart. Backup is root-only
/root/tolf-eaptls-dynamic-stage-20261009/test.before-b-internet.
Existing B SA keeps the old selectors until reconnect.

Read-only checks: Moscow source-pool route for 1.1.1.1 uses table 100 GRE Riga;
RU-marked route for 77.88.55.80 uses Moscow br-lan. Riga has return route for
10.10.10.0/24 through gremoscow and outbound NAT on ens3. Moscow DNS
10.254.0.53 resolves whoer.net and yandex.ru. These are server-side checks,
not live end-to-end Windows Internet acceptance.
Windows profile still has only the ping route; read its scope/routes and the
management-host 10.0.21.10 route before adding broad IPv4 VPN routes.
IPv6/browser behavior and effective DNS remain to be checked separately.
