## Failed on Windows 10 — do not install

Client Event 12 at 12:20:53 on 8 October 2026 returned 0x82AA0002 at the diagnostic NativeProfile node. The merged direct-CSP candidate did not create the VPN connection. It is retained solely as a failed diagnostic artifact. Production personalization was not changed.

# Windows crypto diagnostic

TOLF-Crypto-Check.ppkg is a diagnostic package, not a usable VPN account.
It installs only the all-user profile
TOLF Crypto Check 734b2c87-0b23-4786-a73d-4d7e4e311798.
It does not install a client certificate or a CA, connect automatically, or
modify the working TOLF profile. Do not connect this diagnostic profile.

All runtime values use one NativeProfile and one CryptographySuite via native
VPNv2 CSP characteristics. No ProfileXML, executable or script is installed.
Expected readback: SHA256128, AES256, Group14, AES256, SHA256, None.
A successful code/container check is not proof of successful Windows readback.

The base container was personalized with throwaway synthetic material; both
certificate runtime groups and their provisioning files were removed and the
resulting WIM extracted and checked. No production credential is in this file.
