# TOLF iOS VPN Shortcuts — experimental

Two deterministic commands for the same device-specific VPN connection:

- **TOLF ON:** Set On Demand = On, then Connect VPN.
- **TOLF OFF:** Set On Demand = Off, then Disconnect VPN.

The original signed MobileConfig, client certificate, and existing Cisco
connection are not modified by adding these Shortcuts.

## Build and distribution

The Cherri v2.3.0 source definitions are in cherri-on.cherri and
cherri-off.cherri. GitHub Actions validates them and checks that each
compiled workflow contains exactly two Apple Set VPN actions with the
correct order, On Demand value and two setup questions for the VPN target.

Cherri on Linux uses RoutineHub HubSign to create Apple-signed Shortcuts.
Both experimental artifacts were successfully signed this way on
October 10, 2026 without an interactive iCloud login.

The signed files are staged under shortcuts/signed/ and exposed by the
experiment page at /shortcuts/experiment.html.

The user may have to choose the same installed TOLF AnyConnect VPN for
each of the two Shortcuts import questions. This behavior and the correct
handling of WFVPN by iOS 26 have NOT yet been tested on an actual iPhone.

Do not merge this experiment into the production MobileConfig installer
until the end-to-end iOS test succeeds. Keep the ability to roll back
without affecting the working VPN profile.

## Developer fallback

The offline Python draft builder in build.py produces unsigned files,
not installable on iOS. sign-on-mac.sh is retained as a Mac signing fallback
but is not needed for the current Cherri + HubSign build pipeline.
