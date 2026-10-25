# Bank transfer invoice pilot

An active administrator account is required throughout this pilot.

## Setup

Open /admin/bank-payments.html. Enter the beneficiary, bank, IBAN, BIC/SWIFT, confirmed VAT registration status and VAT number when applicable. Enable invoice issuing and save. No guessed or test bank account is installed in production.

## Workflow

The billing form collects buyer details. The server calculates the price for 50-1000 GB, snapshots all invoice details, allocates a unique annual number and stores an immutable pro forma PDF. Its number is the payment reference. Invoice issuance does not credit traffic.

An administrator verifies actual incoming funds and records the exact EUR amount, bank transaction ID and receipt date. Confirmation, traffic credit, audit entry and receipt PDF commit atomically. Duplicate confirmations do not credit twice. A transaction cannot settle two invoices. Partial or mismatched amounts remain unconfirmed.

Owner and administrator document routes enforce authorization. Existing PDFs remain unchanged after settings edits. Montonio notifications cannot settle bank-transfer orders.

These documents are advance-payment requests and payment confirmations, not generated VAT invoices. No tax status or rate is guessed.

## Checks

API/DB tests: setup/payments/test_bank_transfer.py.
Mocked browser workflow: tests/bank-invoices-browser.cjs; set TOLF_PLAYWRIGHT to the installed module path. The browser test intercepts all API requests.
