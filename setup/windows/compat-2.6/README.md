# Deployed Windows 2.6 API compatibility

The user supplied the exact deployed module (normalized SHA256
`3a433a1842a9fee59dfee99700824659b4e332d3cabdd2cb6119a092e29fbe12`,
23070 bytes). It is preserved in `tests/windows/fixtures/windows-2.6.0.py`.
It adds Moscow device metadata and password reveal/rotation, which are absent
from the historical 2.3 source. Do not allow the 2.3 binary updater to replace it.

`tolf_windows.py` in this directory is that deployed source with routing added.
It preserves `windows_device_nodes`, `windows_password_changes`, native installer
version 2.6.0, existing setup links, and four-field native settings responses.
Existing Moscow devices default to Moscow's empty Local ID; Riga devices to sr.

Run `python3 setup/windows/build-routing-2.6.py` to generate the self-contained
London updater `setup/windows/update-routing-2.6.py`. The updater accepts only the
verified deployed source or its own output. It backs up the API and database,
updates two Python modules, checks local API health, and verifies the executable
checksum has not changed. It never installs or downgrades the Windows executable.

The already-installed Riga controller remains disabled until a separate enable
step. The API continues to expose both existing node defaults while it is disabled.
Routing selection still requires a real Windows handshake test before wider use.
