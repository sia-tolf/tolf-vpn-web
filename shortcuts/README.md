# TOLF iOS VPN Shortcuts

Two fixed, non-toggle shortcuts. All actions target the same locally selected
TOLF AnyConnect VPN configuration.

- TOLF ON: Set On Demand = On, then Connect VPN.
- TOLF OFF: Set On Demand = Off, then Disconnect VPN.

The native iOS Set VPN action handles both steps. No web request, private
key or TOLF API token is embedded in the shortcut.

## Build

Run on any computer:

    python3 shortcuts/build.py

This creates unsigned drafts only. iOS 15+ cannot import those drafts.

## Sign once as the publisher

On a Mac logged into an Apple Account in iCloud, execute from the repo root:

    bash shortcuts/sign-on-mac.sh

Apple's Shortcuts CLI signs both files with the anyone mode.
Apple validates the signed workflow and may require network access. Signed
files appear under shortcuts/signed/; they can be hosted by TOLF for
all users. End users do not need the publisher's Apple Account.

## Device-specific VPN selection

TOLF MobileConfig installs a VPN with a per-device identifier and label.
The installer therefore must resolve the two VPN-target parameters locally.
Two import questions per shortcut ask the user to select the same TOLF VPN.
Do not claim the selection is automatic until confirmed on iOS 26.

Until signed shortcuts pass an actual iPhone test, do not publish download
buttons on the production TOLF website.

## Current CI blocker

A macOS GitHub Actions runner has the shortcuts tool but no iCloud login.
Apple returns: In order to do this, you must be signed into iCloud.
Do not put Apple Account passwords or tokens in GitHub Actions secrets.
