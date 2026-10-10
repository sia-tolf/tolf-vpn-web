# TOLF VPN Shortcuts — native-export builder

The working reference is the owner's Apple-exported ON shortcut, confirmed on
iPhone on 2026-10-10. Keep this device-specific source outside the repository.

`build.py --source /path/to/working-on.shortcut` builds unsigned commands:
- ON preserves the native source workflow exactly.
- OFF changes only WFOnDemandValue=false and WFVPNOperation=Disconnect.
- Both steps retain the full native WFVPN object, including appDescriptor.
- No text VPN placeholders, synthetic UUIDs, or import questions are generated.

The source is an unsigned binary/XML plist (the shortcut asset in the iCloud
record), not the encrypted signedShortcut asset.

## Signing
Unsigned builds cannot be installed directly on iPhone.
`sign-on-mac.sh /path/to/working-on.shortcut` signs locally with Apple Shortcuts.
`sign-native.py --source /path/to/working-on.shortcut --output /path/to/output`
uses RoutineHub HubSign and sends the workflow, including the VPN name, local
identifier and app descriptor, to that external service. Obtain explicit owner
authorization before using it with a real device export.

ON structural equality and OFF's exact two-parameter difference are checked
offline by tests. A newly signed/imported OFF still requires an iPhone check.

## Retired experiments
cherri-on/off and the probe files are historical experiments, not the current
distribution source. The earlier TOLF-VPN-Check contained filter.vpns, which the
iPhone reported as Unknown Action. The earlier text-based WFVPN import binding
does not match the native export. The experiment page remains paused until
replacement signed commands are available and verified.

## Return to the Home Screen

Use --return-home with build.py or sign-native.py to append the native Go to Home Screen action after both VPN operations. URL launching still opens Shortcuts briefly; the final action returns Home. Names and VPN binding remain unchanged.
