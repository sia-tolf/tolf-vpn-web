# Montonio sandbox integration

This module is sandbox-only. It never modifies live traffic balances or enforcement.

## Deployment
- Runtime: Python 3, FastAPI and PyJWT >=2.10,<3. Install PyJWT with umask 022 so the tolfa service can read it.
- Store keys using store-sandbox-keys.py on UK. Keep /etc/tolf-payments mode 0750 root:tolfa and its JSON mode 0640 root:tolfa.
- Pin storeUuid from authenticated GET /stores/payment-methods and reviewerIds to the ordinary reviewer account UUID. Existing TOLF administrators may also test their own sandbox account.
- Copy tolf_billing_sandbox.py to /opt/tolf-api/ mode 0644, back up main.py, append import tolf_billing_sandbox and tolf_billing_sandbox.install(app, globals()). Restart tolf-api and verify /billing/capabilities.
- Database /var/lib/tolf-api/montonio-sandbox.db is owned by tolfa, mode 0600. Never merge its credits into the live ledger.
- Public billing/sandbox.js upgrades the preview only when authenticated /billing/capabilities explicitly enables sandbox for that account.
- Hosted sandbox URLs may use sandbox-checkout.montonio.com, sandbox-gateway.montonio.com or sandbox-stargate.montonio.com. No live URL or fallback is accepted.
- The return token is validated but does not create credits. Signed webhook or authenticated provider GET verification credits exactly once.
- Tests: pytest tests/payments/test_sandbox.py and node tests/payments/frontend.cjs with TOLF_JSDOM pointing to jsdom.

## Limits before production
This is a review environment, not a live billing launch. Trial activation, real balance enforcement, automatic refund initiation, fiscal invoice issuance and production activation still require implementation and acceptance. Refund requests remain a support process; no refund button is exposed. Do not mark all commercial-launch checks complete merely because a sandbox purchase works.


## Sandbox records (2026-10-22)
- Install reportlab >=4.4,<5 and pycountry >=24,<25 in the API virtualenv (umask 022), plus fonts-dejavu-core on Debian. Copy both tolf_billing_sandbox.py and tolf_billing_records.py to /opt/tolf-api/.
- Startup adds tables without rewriting orders/credits. Existing verified paid sandbox orders receive a lot and a TEST purchase confirmation exactly once. PDFs are stored as immutable blobs and repeat downloads return identical bytes. Buyer details and seller/tax-policy snapshots are frozen at issuance.
- Customers can optionally add individual/company billing details. No mandatory residency selector. No full card number, CVC, full payer IBAN or raw provider payload is retained.
- Observed authenticated sandbox GET /orders on 2026-10-22: card paymentIntents.paymentMethodMetadata is empty; paymentMetadata supplies cardPaymentPricingGroup only. Bank metadata supplies preferredProvider, preferredCountry, providerName and receiverIban (MERCHANT recipient). These do not establish payer residence. preferredCountry is gateway routing (international banks share codes across lists). billingAddress is merchant/customer supplied, not independently bank-verified.
- country_evidence stores explicitly classified country observations only. taxCountry stays null/unresolved. No inference from language, server city, method name, pricing group, bank BIC or merchant receiving account. Adding independently verified payer-country fields requires documented semantics and tests.
- VAT policy sandbox-tax-unconfigured-20261022 explicitly does not claim exemption or 0% VAT. All receipts say TEST and are NOT VAT invoices. No production launch until tax treatment and required location evidence are established.
- Package lots use decimal GB (1 GB = 10^9 bytes), FIFO usage and immutable purchase/usage/refund events. Actual VPN traffic is NOT attached. The admin-only /billing/sandbox/admin/usage test endpoint records idempotent simulated usage with eventId, userId, bytes.
- Refund initiation is not exposed. Authenticated GET reconciliation of successful provider refunds creates separate test correction documents and revokes proportional unspent test traffic. Signed sparse paid/refund notifications update order state and schedule an authenticated provider GET in a background task for complete metadata and refunds. Owner GET can retry if the provider is unavailable. No correction replaces an original PDF.
- Month exports (UTC), admin-only: /billing/sandbox/admin/export.csv?month=YYYY-MM&kind=purchases|movements|balances|fees. Purchase export is document ISSUE month (historical migration issue time may differ from original paid date); both timestamps are shown. Balance export reconstructs month-end events, not today's balance. Value estimates are NOT posted revenue and do not allocate SmartDNS. Null fees remain blank, not zero. Provider fees are latest observed data for payments in that paid month. This is NOT a settlement/payout reconciliation: provider payout reports are not yet integrated.
- Accountant exports are on the billing page for authenticated admins only. Ordinary reviewers can download only their own PDFs. CSV text fields are formula-escaped.
- No trial activation, live crediting, tax-threshold monitoring, tax registration automation or accounting bookings are enabled. Production and sandbox number series remain separate.


### Prepared deployment
Deployment explicitly approved by the user on 2026-10-22 after automatic review initially requested specific approval. API modules installed, restarted and verified. Online SQLite and module backup: /opt/tolf-backups/billing-records-20261022-074740. Frontend publication follows the verified backend. Live payments remain disabled.
Before approved deployment:
1. SQLite online backup of montonio-sandbox.db and copies of installed payment modules under /opt/tolf-backups/billing-records-UTCSTAMP (0700).
2. Install dependencies from requirements.txt with umask 022, fonts-dejavu-core, then copy both modules mode 0644. Restart tolf-api.
3. Verify service readiness and authenticated reviewer capabilities, paid-order PDFs, owner isolation and unchanged live balances.
4. Publish billing/index.html, page.css, sandbox.js together after backend checks.
5. Reconcile existing paid sandbox orders via authenticated provider GET; verify country remains unresolved for currently observed sandbox metadata.
Rollback: restore prior installed sandbox module and remove its new records import by restoring the old file. Added tables can remain unused; do not restore a stale database over newer payment events. If reverting database is required, stop writes and reconcile provider payments first.


## Post-payment billing details
Authenticated owners can POST /billing/sandbox/orders/{reference}/billing-document with {buyer:{kind,name,address,country,registration,vatNumber}} for paid/refunded purchases. Origin and payload checks apply. A new immutable billing_details supplement links the original purchase and freezes its seller/tax/amount snapshot. The original PDF and checkout details are never overwritten. Same details return the same document; different details after issuance return 409 and require support. If the original purchase document already has billing details, it is returned without a duplicate.
Supplements are excluded from financial purchase export rows to avoid counting a sale twice; exported buyer details use the supplement when present. They do not credit/debit traffic, trigger payment or create ledger events. Sandbox output remains a test purchase confirmation, not a fiscal invoice. The three-language history UI opens an accessible dialog for optional post-payment details and downloads the resulting PDF.


## Document language and traffic precision
New documents are English by default, independent of checkout/UI language. Documents containing buyer billing details with country LV are Latvian. A post-payment billing supplement selects its own language from the supplied billing details. Previously issued immutable PDFs are not regenerated.
User-visible total traffic balance and per-package remaining traffic always show exactly three decimal places in GB, using the UI locale's decimal separator. Internal accounting continues to store exact integer bytes; display rounding never changes balances.


## Purchase history and presentation (2026-10-22)
- History exposes paid/refunded purchases and pending/uncertain states; terminal unpaid ABANDONED/VOIDED/DECLINED/CANCELLED/EXPIRED orders stay in the database but are omitted from customer history. Pending orders have clear guidance. Continue payment first forces authenticated provider verification using ?resume=true, takes the fresh provider payment URL, and reuses the existing order. A failed verification does not redirect or create a second order.
- Receipt and billing-details actions are equal-width buttons on one row at all viewport sizes. Refund corrections remain available separately.
- Account captions use the existing VPN username (then login name, then public account number) captured in order_identity. Never display the internal UUID as a buyer name. Existing no-details PDFs get a sealed document_presentations rendition with only the technical caption corrected; original financial snapshots and original PDFs remain unchanged in documents. Repeat downloads return identical rendition bytes.
- The balance integer and unit retain the text colour; decimal separator and three fractional digits are rendered at 45% opacity. Exact stored byte balances do not change.

Visual QA: Chromium headless at 1100px and 390px verified equal buyer-control top coordinates on desktop, equal-width invoice buttons on the same row at both widths, no horizontal overflow, and balance integer/fraction split with opacity 0.45. The offline fixture includes paid, pending and abandoned orders and makes no real API/payment calls.


## Billing visual consistency and transient return status
Compact package controls use one headline row: GB, savings badge, price; unit price is below, with no second badge row. Tablet widths stack packages; wide screens retain three columns. Billing colours and action buttons reuse the same TOLF tokens and primary/secondary classes as the VPN page.
Both order-token and sandboxOrder return parameters are removed from the URL immediately after capture, before async verification. Refreshing the cleaned URL loads history without replaying a prior success banner. Switching packages/language or restoring the page from back-forward cache clears transient result text. Persistent payment state remains in history.
