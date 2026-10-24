# New York AnyConnect via Moscow

Status: prepared, not published or activated.

Endpoint: oc-us-moscow.tolf.is:4443, A record 92.243.66.204, DNS only.
Moscow forwards TCP/4443 to 162.252.174.201:4443 and UDP/443 to
162.252.174.201:443. The New York node terminates TLS/DTLS and authenticates
the existing client certificates. Profile names, per-entry UUIDs, routing modes,
revocation, accounting and shortcuts remain owned by the New York entry.

Activation gates:
1. Confirm public DNS A resolves to 92.243.66.204; do not add an AAAA record.
2. Back up Moscow firewall; enable address-specific TCP/UDP forwarding and
   source NAT with persistent configuration. Preserve Moscow's existing VPN
   listener on 92.243.66.32 and management SSH on 92.243.66.204.
3. Provision a publicly trusted server certificate including
   oc-us-moscow.tolf.is and preserve oc-us.tolf.is. Verify automated renewal.
   HTTP/80 challenge forwarding can be scoped to 92.243.66.204 if required.
4. Verify TLS hostname and certificate validation from an independent host;
   verify both TCP-only and DTLS VPN traffic and DNS through the relay.
5. Back up UK API modules and node registry. Change only the US catalog entry
   anyconnect_endpoint, deploy tolf_oc_mobileconfig.py and restart API with
   rollback on health failure.
6. Run profile identity, UI and Windows endpoint-validation tests. Publish the
   matching frontend change only after the server-side endpoint is healthy.
7. Existing profiles retain the old address; users reinstall only the New York
   profile. Existing New York shortcut and webclip names stay unchanged.

Rollback: restore the US catalog endpoint and API module, republish the previous
frontend revision, remove only the dedicated relay firewall sections. Direct
New York endpoint and all Moscow/Riga services remain available.
