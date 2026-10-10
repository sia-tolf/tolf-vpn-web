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
