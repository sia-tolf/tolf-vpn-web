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
and runtime-group identities to each device and captures the result as a WIM
with provisioning metadata. Every produced package is extracted again and its
contents compared to the source payload. Only XML and native provisioning XML
are accepted in the template.

UK runtime files:

- `/opt/tolf-api/tolf_windows.py`
- `/opt/tolf-api/tolf_windows_ca.py`
- `/opt/tolf-api/tolf_windows_certificates.py`
- `/opt/tolf-api/tolf_windows_ppkg.py` (deployed copy of `ppkg/personalize.py`)
- `/opt/tolf-api/windows-ppkg-template` (verified extracted Microsoft template)
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
