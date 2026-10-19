# Riga VPN measurement path

The browser throughput test previously connected to the public VPN gateway IP.
OpenConnect routes that gateway outside its tunnel, so the result could describe
the underlying connection rather than VPN throughput.

Riga now has separate target lists: public entry probes remain available before
connecting; the throughput test uses only
https://speedtest-riga.vpn.tolf.is:8444/ (10.250.80.1).
It never substitutes a public result when the private listener is unreachable.
The browser may request local network access for the private destination.

Deployment requires explicit approval after review:
1. On Riga, run setup/measurements/install-riga-vpn-measurement.py --apply.
2. Validate its TLS certificate, empty response, download and upload.
3. Publish the website change to main.
No VPN daemon restart, worker change, rate cap, new certificate issuance, or
New York deployment is included.
The installer uses Riga's existing wildcard certificate and pinned backend.
Its renewal hook restarts only this measurement service after renewal.

Rollback: revert the website commit; on Riga run the installer --rollback.
The dedicated DNS A record can remain without affecting VPN connections.
