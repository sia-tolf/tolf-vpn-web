# Node session inventory

This first node installer adds only `admin-sessions riga|moscow` to the existing forced-command gateway. It preserves provisioning, certificates, credentials and running sessions. The reader returns selected session metadata and aggregate CHILD_SA counters; it never returns credential material. An empty successful reply differs from timeout, command failure or unsupported output.

`remote-eap-id` takes precedence over `remote-id`. The latter is only a candidate identity: the control plane must match it against its registry before identifying an account. Raw text is used for display only and must not become authorization for destructive operations. Session termination and reversible suspension are still pending.

Build with `python3 setup/admin/nodes/build.py`; install `install-riga-sessions.py` as root on EDISLV. The installer backs up the helper and both gateways, validates shell/Python syntax, and rolls back files if Riga inventory fails. It neither restarts strongSwan nor changes the Moscow host. Moscow is queried using the existing synchronization key with strict host checking. London API and admin UI activation follow node installation.
