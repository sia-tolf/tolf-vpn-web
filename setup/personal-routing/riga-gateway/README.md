# Riga gateway for the enrolled user0 account

Install alongside the existing root and SSH provisioning gates on EDISLV. Stage
`gateway.py`, `install.py`, and the exact `../user0-service/policy.py` together.
Run `python3 install.py` as root. The installer requires the protocol-2 Moscow
receiver to be reachable over the existing strict-host-key SSH channel.

The new command is `personal-routing-user0 status|apply`. Apply accepts a bounded
protocol-2 JSON document on stdin; account identity and domains are validated
before SSH. The destination, key, receiver command and supported account are
fixed. No domain or client-supplied value becomes shell syntax. A matching
accepted revision is not itself evidence of application: inspect appliedRevision,
appliedDigest, state and scope from the receiver.

Installation probes status only. It never submits the older UK database policy.
Existing gates are backed up under `/root/tolf-routing-gateway-backup-*` and
restored on installation failure. The printed rollback script restores gates
only if their hashes still match this installation, preserving later changes.
Helper files are retained but unreachable through restored gates after rollback.
The website/API delivery worker is a separate deployment step.
