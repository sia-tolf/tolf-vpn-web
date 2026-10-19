# Direct measurement bypass for AnyConnect/OpenConnect

Deployed on Riga, Moscow and New York with configuration reloads, without restarting the VPN processes.

Each entry point advertises three split-exclude host routes:
- 188.214.39.114/32 (Riga)
- 92.243.66.32/32 (Moscow)
- 162.252.174.201/32 (New York)

The native OpenConnect network scripts process CISCO_SPLIT_EXC on Windows and Unix. The exclusions use the underlying gateway and apply when the client connects. Existing connections need one reconnect; there is no need to disconnect the VPN between direct tests of different cities.

Only these host routes are added. Existing route and exclusion entries are retained. append-global-routes keeps the managed exclusions when an account/group has its own configuration. Server-side profile routing and private VPN measurement endpoints are unchanged.

The browser checks the public measurement listener's getIP response before and after a direct test. It rejects known TOLF egress addresses and private tunnel addresses, fails closed on an unreadable response, and clears the result if direct access cannot be re-confirmed. The visitor IP is neither stored nor displayed by this guard. This verifies bypass of the managed TOLF tunnel; it cannot detect arbitrary third-party VPN/proxy services.

install-direct-bypass.py is read-only by default; --apply validates each candidate using ocserv --test-config, preserves a backup and reloads through the node's control socket. It is idempotent and preserves global/vhost scope. If reload fails the configuration is restored from its backup. Nodes apply sequentially, so after a failure rerun the read-only check before continuing.

Rollback: restore the saved configuration for the affected node and use its occtl reload command. The Debian backups are under /var/lib/tolf-measurements/direct-bypass-20261019/ and the OpenWrt backup under /root/tolf-direct-measurements-20261019/. Affected clients reconnect to receive the earlier routing policy.

Scope: this change advertises OpenConnect/AnyConnect exclusions. It does not modify IKEv2 profiles or other VPN clients' operating-system route tables. The route guard still prevents known TOLF-tunneled requests from being labelled direct.
