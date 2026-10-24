# New York AnyConnect via Moscow

Status: server relay and dual-name certificate verified; API deployed with selection disabled until frontend publication.

Endpoint: oc-us-moscow.tolf.is:4443, A record 92.243.66.204, DNS only.
Moscow uses a dedicated inet tolf_ny_relay nftables table and init service.
Moscow forwards TCP/80 for HTTP-01 renewal, TCP/4443 to 162.252.174.201:4443 and UDP/443 to
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
5. Back up UK API modules and node registry. Deploy the request-scoped endpoint selector and catalog-aware API candidates;
   leave the global US node catalog unchanged. Enable the RU-only gate after
   TLS and VPN verification, restart API with rollback on health failure.
6. Run profile identity, UI and Windows endpoint-validation tests. Publish the
   matching frontend change only after the server-side endpoint is healthy.
7. Existing profiles retain the old address; users reinstall only the New York
   profile. Existing New York shortcut and webclip names stay unchanged.

Rollback: restore the US catalog endpoint and API module, republish the previous
frontend revision, remove only the dedicated relay firewall sections. Direct
New York endpoint and all Moscow/Riga services remain available.

Selection is per request, using the existing Russian RIPE allocation classifier.
Only Russian source IPs use the relay when ny-moscow-relay.json enabled=true.
Non-Russian and unknown addresses keep the direct endpoint. No global DNS or
US catalog replacement is required. The candidate API modules are based on
the current live catalog-aware implementation and remain undeployed.


Verified on 24 October 2026:
- Independent OpenConnect client through Moscow: TLS certificate validation,
  DTLS connection, HTTPS exit IP 162.252.174.201, internal DNS success,
  three successful ICMP probes.
- TCP-only OpenConnect through the relay: HTTPS exit IP 162.252.174.201.
- Both public TLS hostnames validate against the same dual-name certificate.
- Russian / non-Russian / unknown IP selection, gate disabled or malformed,
  unchanged Moscow/Riga catalog, stable iOS profile UUID and English name.
- Quick installer tests pass with both direct and relay New York endpoints.
- Six legacy mobileconfig tests pass.
- Existing broad UI test still fails on the network metrics heading assertion;
  the identical failure reproduces on the unmodified b1ae277 baseline.

New York ocserv uses the new Certbot-managed certificate paths, both hostnames
included. Certbot standalone HTTP-01 renews via each public A record. A dedicated
deploy hook validates the config and reloads ocserv after renewal. The relay's
public IP is excluded from client tunnel routes. The former node certificate
automation can keep its separate PKI files; ocserv no longer references them.

Existing installed New York profiles retain their original address until
reinstalled. Country is determined at profile/setup issuance, not at each VPN
connection. This change covers AnyConnect setup for iOS, Android and Windows;
IKEv2 ingress endpoints are not changed.
