# TOLF VPN — Microsoft Store preparation

Status: preparation draft, not a submission-ready package. No Store submission
has been created and no certification or Store identity is claimed.
Source baseline: Windows 2.6.1, commit 5f22ca2e2e8e0ab4b60648a628ee5a0976d3366e.
The existing website, London API and downloadable EXE release are unchanged.

## Publisher step

Open https://storedeveloper.microsoft.com/ and sign in to the intended publisher
account. For publication by the TOLF business use a Company account. Complete
Microsoft's business verification if not already registered. Reserve `TOLF VPN`
if available; availability has not yet been checked in Partner Center.

In the product, open Product management → Product identity. Copy these exact
non-secret values into identity.json (not passwords or signing keys):

```json
{
  "identityName": "COPY Package/Identity/Name",
  "publisher": "COPY Package/Identity/Publisher",
  "publisherDisplayName": "COPY Package/Properties/PublisherDisplayName"
}
```

Render the draft manifest with:
`python store/msix/render-manifest.py identity.json OUTPUT/AppxManifest.xml`

## Native application adaptations still required before packaging

1. Make normal packaged launch open the controller, with a visible Add connection
   action opening the setup screen. Retain the widget and RU/SR labels.
2. Obtain personal settings using the existing HTTPS setup link pasted by the
   user. A Store executable has a common filename and cannot carry a token in it.
   Later optional website-to-app activation must validate the exact allowed
   scheme/host/token and require user confirmation before any configuration.
3. In a packaged process, run the controller from its installed package path.
   Do not copy the EXE into versioned LocalAppData, create desktop/Start links,
   or use self-update mechanisms. Store owns installation and updates.
4. Replace the Startup-folder shortcut with a package startup task. It must be
   user-controlled and must not automatically connect VPN just by installing.
5. Verify real RAS phonebook access under package identity: current code obtains
   RoamingAppData and uses Microsoft/Network/Connections/Pbk/rasphone.pbk while
   WMI provisions the Windows current-user phonebook. Packaged path/registry
   virtualization must not split those operations into different locations.
   Do not blanket-request unvirtualizedResources without a demonstrated need.
6. Verify migration/discovery of existing profiles, passwords, HKCU labels and
   exclusions. Keep RAS names/UUIDs; never recreate users or overwrite modes.
7. Test Store install/update/uninstall with two profiles: Riga/RU and Riga/SR,
   RDP peer exclusion, reconnect, password update, widget/tray, and startup.
   Uninstall behavior for system VPN profiles must be explicit in the UI/listing;
   deleting the application must not silently delete the TOLF server account.

## Submission material

- Draft listing: listing-en.md. Review before sending to Store.
- Draft manifest: msix/AppxManifest.template.xml. It deliberately contains
  placeholders; it is not a runnable package and does not claim certification.
- Initial target: x64 Windows desktop. Minimum build is a draft baseline and
  needs to match packaged testing results; do not advertise ARM64 or Windows 10
  compatibility until verified.
- Required capability: runFullTrust, because the existing native desktop app
  uses RAS and WMI to configure Windows IKEv2 connections as the current user.
  This is not a UWP packet-processing VPN plugin; do not add vpnProvider merely
  because the product is a VPN controller. Document capability rationale for
  certification.
- Produce Store-size icons from the existing TOLF monogram and real screenshots
  of the packaged build; EXE-only screenshots do not verify packaged behavior.
- Confirm support/privacy URLs, prices, markets, age-rating questionnaire and
  data disclosures with the publisher. Existing privacy text needs review for
  Windows credentials, per-device labels, exclusions and server traffic.
- Create dedicated reviewer test access shortly before submission. Do not use
  protected user0/user0_ipad accounts or publish bearer links in the repository.
- Run Windows App Certification Kit and packaged runtime checks, then attach
  exact-identity MSIX to the Partner Center draft. Store signs after approval.

## Primary references (checked 2026-09-15)

- https://learn.microsoft.com/en-us/windows/apps/publish/view-app-identity-details
- https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/app-package-requirements
- https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/create-app-submission
- https://learn.microsoft.com/en-us/windows/apps/desktop/modernize/desktop-to-uwp-extensions
- https://learn.microsoft.com/en-us/windows/msix/desktop/flexible-virtualization
