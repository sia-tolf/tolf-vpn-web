# Ordered website groups

The API returns groupingAvailable: true and routingGroups, an object with
the same exit keys as routingRules. Each exit contains an ordered array of
nonempty domain arrays. The flattened groups must exactly match routingRules;
duplicate domains, mismatches and cross-exit parent/subdomain conflicts are
rejected. Both domain and group order are retained.

An additive nullable groups_json column stores grouping metadata. Existing
rows appear as one group per domain without modifying saved rules or revisions.
Group edits use account authentication, origin checks, operation locks
and revision conflict protection. Older clients retain surviving groups and
append newly added domains as singleton groups.

Delivery continues using flat routingRules. The browser enables grouped editing
only when the API advertises support. Before the upgrade, existing rows and
saves still work.

Run install-groups.py with /opt/tolf-api/venv/bin/python on EDISUK, with the new
tolf_personal_routing.py beside it. The installer requires the known previous
delivery API hash, makes a consistent database/code backup, adds the column,
validates existing policies, replaces only the API module and restarts tolf-api.
On failure it restores the previous module without replacing the live database.
Its printed rollback command retains the additive column and data.
