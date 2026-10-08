# Machine-certificate ProfileXML validation fixture

Source: https://learn.microsoft.com/en-us/windows/client-management/mdm/vpnv2-csp
Section: ProfileXML XSD Schema. Retrieved 2026-10-08.

This is a machine-certificate-only projection of the published XSD.
Only the external EAPHost schema import and the Eap element are removed.
Root, NativeProfile and CryptographySuite element sequences, occurrence rules
and types remain those from the source. It is not the internal
Windows schemas/VpnProfile/VpnProfileSchema.xsd schema.

These tests validate our existing MachineMethod=Certificate payload only.
They do not validate EAP-TLS, provisioning/CSP behavior, certificate selection
or Windows installation and handshakes.
