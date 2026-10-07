The certificate delivery implementation is described in [CERTIFICATE-DEPLOYMENT.md](CERTIFICATE-DEPLOYMENT.md). Personal PPKG delivery is enabled; actual Windows installation/connection still needs a client test.

# Windows IKEv2 PPKG without EXE — 7 October 2026

## Verified build

Windows Configuration Designer 10.0.26100.9457 compiles a genuine PPKG with
native IKEv2, EAP-MSCHAPv2, AES256/SHA256/Group14, PFS None, ForceTunnel,
and credential caching. The package contains no EXE, DLL, script, or command
payload. DISM extraction and independent Linux wimlib extraction verified
the actual runtime provxml, not only the customization source.

Successful build and full payload verification:
https://github.com/sia-tolf/tolf-vpn-web/actions/runs/37659096949

Test package:
https://github.com/sia-tolf/tolf-vpn-web/releases/tag/windows-ppkg-33efcf4f690126a58e23f6aac02a1c4b536b7b46

This sample creates a profile named TOLF PPKG Test pointing to Riga. It
contains no production identity, username, password or activation token.
Windows 10/11 installation and VPN connection are NOT yet tested. The
compiler runs on Windows Server 2022, which is not a Windows 10/11 client.

## Compiler schema extension

The default WCD VPN schema omits CryptographySuite. This is a compiler
schema limitation, not evidence that native Windows provisioning cannot
apply the settings. On the build machine only, the build copies the Desktop
settings store, adds six string settings mapped to documented VPNv2 native
CryptographySuite CSP paths, and compiles against the extended store.

The earlier proposal that an EXE was required for crypto was premature.
No embedded executable implementation is used or planned in this workflow.
The extended schema itself is not installed on the user's Windows device.

## Credentials remain separate

RememberCredentials means caching credentials after they have been
provided; it does not inject a username/password. Automatic credential
delivery in a settings-only PPKG remains unverified and unimplemented.
Do not claim complete unattended VPN setup. In this prototype the user
would supply valid VPN credentials separately when first connecting.

## Files

- profile.py: native ProfileXML source.
- customization.py: WCD namespaces, collection structure and crypto settings.
- build-prototype.ps1: build-only compiler schema extension, ICD compilation,
  DISM extraction and payload validation.
- verify-package.py: validates exact runtime provider paths and values,
  EAP type, server and absence of executable/command payload.
- tests/windows/fixtures/native-crypto.provxml: actual compiled sample.
- .github/workflows/windows-ppkg.yml: synthetic build only; no real credentials.

## Remaining delivery work

1. Test actual Windows 10/11 installation, crypto, credential prompt and VPN
   connection. Home edition support is not established by VPNv2 docs.
2. Implement per-device package creation on the UK control plane; preserve
   separate Windows identities, expiry and revocation checks.
3. Resolve credential delivery without introducing an embedded EXE or script.
4. Enable website download and native iOS sharing after client validation.
   Reuse a prepared File object from a user-initiated sharing action.

Manual Windows preparation is available from iPad/any platform. Quick
Windows setup is restricted to the Windows computer where the site is open.

## Primary references

- https://learn.microsoft.com/en-us/windows/configuration/provisioning-packages/provisioning-command-line
- https://learn.microsoft.com/en-us/windows/configuration/provisioning-packages/provisioning-multivariant
- https://learn.microsoft.com/en-us/windows/client-management/mdm/vpnv2-csp
