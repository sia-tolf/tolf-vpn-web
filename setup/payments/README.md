# Montonio sandbox integration

This module is sandbox-only. It never modifies live traffic balances or enforcement.

## Deployment
- Runtime: Python 3, FastAPI and PyJWT >=2.10,<3. Install PyJWT with umask 022 so the tolfa service can read it.
- Store keys using store-sandbox-keys.py on UK. Keep /etc/tolf-payments mode 0750 root:tolfa and its JSON mode 0640 root:tolfa.
- Pin storeUuid from authenticated GET /stores/payment-methods and reviewerIds to the ordinary reviewer account UUID. Existing TOLF administrators may also test their own sandbox account.
- Copy tolf_billing_sandbox.py to /opt/tolf-api/ mode 0644, back up main.py, append import tolf_billing_sandbox and tolf_billing_sandbox.install(app, globals()). Restart tolf-api and verify /billing/capabilities.
- Database /var/lib/tolf-api/montonio-sandbox.db is owned by tolfa, mode 0600. Never merge its credits into the live ledger.
- Public billing/sandbox.js upgrades the preview only when authenticated /billing/capabilities explicitly enables sandbox for that account.
- Hosted sandbox URLs may use sandbox-checkout.montonio.com or sandbox-stargate.montonio.com. No live URL or fallback is accepted.
- The return token is validated but does not create credits. Signed webhook or authenticated provider GET verification credits exactly once.
- Tests: pytest tests/payments/test_sandbox.py and node tests/payments/frontend.cjs with TOLF_JSDOM pointing to jsdom.

## Limits before production
This is a review environment, not a live billing launch. Trial activation, real balance enforcement, automatic refunds, accounting document delivery and production activation still require implementation and acceptance. Refund requests remain a support process; no refund button is exposed. Do not mark all commercial-launch checks complete merely because a sandbox purchase works.
