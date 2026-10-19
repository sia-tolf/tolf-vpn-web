# New York VPN-only measurements

Endpoint: https://speedtest-us.vpn.tolf.is:8444/ at 10.250.81.1.

Deployed after explicit approval on 2026-10-19. No VPN restart or routing changes.

The dedicated single-hostname certificate is issued on Riga as tolf-speedtest-us-vpn using the existing Certbot DNS challenge credentials. Certbot renewal is enabled there. Private key material is never committed or returned in command output.

On UK, retain relay.py and the two tolf-vpn-measurement files under /opt/tolf-measurement-us-vpn-20261019/. Initial installation uses relay.py --install; it refuses unrelated existing target files. Install the tolf-us-measurement-cert-sync units on UK. The timer runs relay.py --sync twice daily. It reads the dedicated certificate over pinned SSH and sends it over pinned SSH to New York. Only a changed certificate restarts the private measurement service. A no-change delivery was tested successfully under the hardened systemd unit.

The New York service guarantees its loopback address before startup, loads TLS with systemd credentials and binds only to the private address. The existing public measurement service remains independent.

Validation: trusted hostname TLS, wildcard CORS response, exact 1048576-byte download, confirmed 65536-byte upload, no-change certificate delivery, enabled renewal/delivery timers, unchanged VPN/public measurement PIDs. Real browser throughput still depends on the client VPN path.

Rollback: set the website us.vpnReady flag to false, disable the UK delivery timer, disable/remove only the new private measurement service and its configuration/credential files, remove the owned private loopback address and DNS record, and remove the dedicated Certbot certificate if no longer used. Do not restart the VPN service or modify the public measurement service.
