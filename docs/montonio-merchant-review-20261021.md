# Montonio onboarding — 21 October 2026

## Business model for review
SIA “Tolf” (Latvia, registration number 40203551237) operates TOLF, a VPN connectivity and SmartDNS service. Customers will purchase prepaid data packages of 50, 200 or 500 GB in EUR. This is a digital service; there are no physical goods, delivery fees, subscriptions or automatic recurring charges. Paid traffic has no expiry date. A planned 1 GB trial is available once per registered account. The configurator is free without registration.

Customers choose a package on vpn.tolf.is, sign in, review the terms and proceed to Montonio hosted checkout. On receipt of a verified successful payment notification, TOLF will credit traffic to that customer's account exactly once. Account balances and usage are managed by TOLF. Montonio handles payments; TOLF does not receive the full card number or card security code.

## Actual readiness — do not claim payment testing is complete
- Public company/contact page and terms prepared in English, Latvian and Russian.
- Privacy page updated with controller identity and planned payment processing.
- Ordinary reviewer account created and /me login verified; credentials are stored outside git.
- Sandbox checkout and signed order notifications are implemented, restricted to the reviewer and existing administrators. Unit/security and UI tests pass. End-to-end provider results are recorded separately below. Other accounts still see the preview.
- Live payments, traffic crediting and commercial quota enforcement remain disabled.
- Do not reconfirm the merchant application as complete until the sandbox tests below pass.

## Required next inputs
1. Sandbox keys have been stored on UK and accepted by the authenticated provider API. Keys must never enter git, HTML, browser storage or logs.
2. Merchant reviews final prices/taxes and the terms, including the proportionate-service withdrawal policy, before checkout is activated.
3. Merchant provides the requested residence-permit copy directly to Montonio through their verified secure channel. Do not place identity documents on the public site or in git.

## Implementation acceptance criteria
- Server controls SKU, EUR price and traffic amount; browser cannot choose price or account ID.
- Explicit acceptance of versioned terms and separate express request for early service provision recorded before ordering.
- Use only sandbox-stargate.montonio.com during review; no production fallback.
- Methods returned by the merchant API; do not infer enabled wallets from user-agent alone.
- Hosted checkout redirect; no card-data fields on TOLF.
- Server verifies notification signature, merchant identity, order ID, amount and currency.
- Transactional idempotency: one order produces at most one traffic credit.
- Return URL alone never credits traffic.
- Test balances and sandbox transactions isolated from real traffic.
- Test successful, declined, cancelled and pending orders, repeat notifications, invalid signatures, wrong amounts, interrupted redirects, other-account access, retry and refund paths.
- Display test mode prominently; retain order references and status history.
- Reviewer has only their own ordinary account; no admin or other-user access.
- Only after documented sandbox evidence and merchant approval, request live keys and proceed to launch checks.

Sources:
https://help.montonio.com/en/articles/217849-website-checklist-for-montonio-merchants
https://docs.montonio.com/api/stargate/checklist
https://docs.montonio.com/api/stargate/guides/orders
https://www.ptac.gov.lv/lv/atteikuma-tiesibas
