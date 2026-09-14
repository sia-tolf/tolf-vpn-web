# Test #26 reversible access control

Restricted to `user_0888048cac6e44d28aed9857aa31e9ed` on Riga and Moscow.
Install `install-riga-test-access.py` as root on EDISLV, then the Admin 1.3
`install-tolf-admin.py` on EDISUK. Neither installer suspends users, reloads
VPN credentials or terminates sessions. The node installer backs up files and
checks existing VICI connectivity; unknown script layouts abort installation.

Suspend first checks identical credentials on both nodes and the existing
Moscow permission. It saves the exact Riga credential in a root-only vault,
persists a `suspending` record, removes the active credential files on both
nodes, reloads credentials and terminates only authenticated Test sessions
using the previously tested native VICI bridge. The result is `suspended`
only after both credential removals and session termination are confirmed.
Credential reload uses the existing swanctl mechanism; no daemon restart.

Resume checks the saved credential hash and Moscow permission, restores the
same bytes on both nodes, reloads and records `active`. No profile or password
rotation is performed. Incomplete operations remain `suspending` or `resuming`
and can be completed or reversed explicitly. There is no automatic rollback
that would silently re-enable suspended access. During a partial resume one
node might already allow access; the UI must not label it fully suspended.

State and the root-only vault are under `/var/lib/tolf-admin/test26-access`.
The provisioning guard blocks this username's create/profile/rotate/delete
operations while non-active, including linked and explicit-username paths.
The synchronization guard serializes Test pushes/deletions with access changes
and refuses them while non-active. Other usernames bypass this guard. Lock
order is provision lock then Test sync lock. Guards never reacquire locks.
State, credential removal and guards persist across reboots.

Access is controlled at the credential level, not by a temporary IP filter.
The scope is this fixed test credential and these known provisioning paths;
root administrators can still edit files directly. General customer suspension
and other credential backends are not implemented by this test feature.

Web changes require the administrator role, exact portal Origin, JSON request,
and validated Test #26 account mapping. The node accepts only fixed actions
and a revision; each operation persists a new revision before changing active
credentials. Old revisions are rejected. API logs request and outcome; unknown
outcomes must be refreshed, not automatically retried.

Build: `python3 setup/admin/nodes/build-access.py`
Tests: `python3 -m pytest tests/admin -q`
