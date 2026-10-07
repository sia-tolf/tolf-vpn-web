# Native Windows PPKG

Windows IKEv2 setup now issues a personal certificate provisioning package.
Manual setup works from iPad and other platforms and offers Save PPKG and native
file sharing. Quick setup uses the same certificate payload on the current
Windows computer.

The PPKG installs settings and a client certificate through native Windows CSPs.
It contains no EXE, scripts or .NET payload. Production keys and package creation
remain on UK; Riga and Moscow receive only public authentication material.

See [CERTIFICATE-DEPLOYMENT.md](CERTIFICATE-DEPLOYMENT.md) for deployed paths,
authorization, packaging provenance and validation. The package has been compiled,
personalized, downloaded and revoked in server tests. Installation and connection
from actual Windows 10/11 still require a client test.
