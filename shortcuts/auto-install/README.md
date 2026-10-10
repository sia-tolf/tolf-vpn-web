# iOS import callback probe
Not wired into the production setup wizard pending a real iPhone import test.

This page requests two sequential imports with nested x-success callbacks:
TOLF ON → TOLF OFF → this page. Cancellation or error returns to this page without downloading a VPN profile.
It does not run either VPN command. The signed files contain the already verified Cisco StartVpnIntent (TOLF Москва iPhone) and StopVpnIntent.

Apple's current x-callback documentation mentions import completion, but documents run-shortcut explicitly.
The import-shortcut URL is documented in older developer material. Neither the Node tests nor serving the files proves that current iOS supports import callbacks.
No successful-install state is written to the production wizard by this probe.

Sources:
https://support.apple.com/en-nz/guide/shortcuts/apdcd7f20a6f/9.0/ios/26
https://swiftrocks.com/running-other-apps-siri-shortcuts-through-deep-links-in-swift

## Result and replacement
The user's iPhone rejected the import callback URL with "Import Failed — The shortcut URL provided was invalid." The probe page no longer uses that route.
It now links to one signed TOLF controller. Two independent equality conditions dispatch on input "on" / "off" to the verified Cisco intents. Missing or unrecognized input does not change the VPN.
The controller and two run links still need iPhone validation before production integration.
URL input reference: https://support.apple.com/en-ae/guide/shortcuts/apd624386f42/ios
Conditional serialization reference: https://github.com/electrikmilk/cherri/blob/main/shortcutgen.go

## Direct launch menu
After the user confirmed that text comparisons now render, direct launch without URL input was found to skip both conditions and execute Go to Home Screen. Added a no-value condition on the materialized Text output containing a Choose from Menu action, with direct Cisco ON/OFF branches. URL input on/off continues to bypass the menu. The final Home Screen action remains intentional.
