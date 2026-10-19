# New York private measurement endpoint (deployed with explicit authorization)

- DNS: speedtest-us.vpn.tolf.is to 10.250.81.1, DNS-only, TTL 300.
- Dedicated public TLS certificate for this single hostname, issued through the existing DNS challenge workflow.
- New measurement-only service on 10.250.81.1:8444, using the existing /usr/local/bin/tolf-speedtest-backend.
- Ensure the private loopback address exists before service startup.
- Use systemd credentials for its certificate and key; no shared wildcard-key export.
- Configure renewal and delivery to the measurement-only service before enabling the UI.
- Validate trusted TLS, CORS, empty response, exact download length and confirmed upload.
- Set MEASUREMENT_TARGETS.us.vpnReady to true only after these checks pass.
- No VPN service restart or VPN routing changes.
- Rollback: disable/remove only the new measurement service, certificate-delivery integration, private address and owned DNS record; restore the UI availability flag.

Deployed 2026-10-19 after explicit user authorization. A dedicated hostname certificate is issued and renewed on Riga; the UK management relay delivers it to the private New York measurement service twice daily. The original VPN and public measurement process IDs stayed unchanged. Trusted TLS, CORS, a 1 MiB download and a confirmed 64 KiB upload passed. Configuration and the credential-safe relay are retained in new-york/.
