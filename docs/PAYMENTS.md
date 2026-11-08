# Khalti payments

## Configuration and current verification limit

The application uses the [Khalti web checkout contract](https://docs.khalti.com/khalti-epayment/), reviewed on 2026-11-06. Configure a merchant sandbox key in private `backend/.env` as `KHALTI_SECRET_KEY`, retain `KHALTI_ENV=sandbox`, and set `FRONTEND_URL` to the exact browser origin (for example `http://localhost:5173`). Restart Django after environment changes. Live mode requires HTTPS and a live merchant key. Keys never reach the frontend or source control.

When configuration is absent, Khalti is disabled in checkout and cash on delivery remains available. The test suite substitutes the provider boundary only; it does not demonstrate a real gateway transaction. No real gateway payment was made during implementation.

## Customer flow

- Select cart items and delivery details, choose Khalti, and submit. The server computes NPR prices and integer paisa, saves an immutable checkout snapshot, and reserves stock before requesting provider checkout.
- The browser follows a validated Khalti URL. An internal payment detail route is saved before navigation so the attempt remains accessible after interruption.
- `/payment/return?attempt=<uuid>&pidx=<identifier>` verifies through a CSRF-protected server lookup. Provider return links containing only `pidx` are also supported. URL status, amount and transaction claims never establish payment success.
- An expired login redirects to sign-in and resumes the return URL afterward. A different account cannot access or verify the payment.
- `/payments` lists the signed-in customer's attempts. `/payments/:id` shows status, references, amount, support/recheck actions and the order receipt when an order exists. Pending and uncertain outcomes never invite another charge.
- A provider-confirmed cancellation, expiry or failure releases reservations and permits returning to the cart. A confirmed completed lookup creates one paid order, decrements inventory once and removes only unchanged selected cart rows.

## Idempotency and recovery

`request_key` is a client-generated UUID. Replaying identical validated input returns its existing payment; reusing the key with different input is rejected. A second key for unresolved cart rows returns HTTP 409 with `payment_id`, and checkout routes the customer to that attempt. An ambiguous browser submission disables further submission on that form and links to payment history. Reloading does not bypass the server's unresolved-payment protection.

Initiation is never retried automatically. An uncertain provider response retains the ledger and reservation; definitive initiation rejection releases it. A missing/malformed redirect cannot become an arbitrary external URL. If a valid `pidx` was returned, it is retained for later lookup.

Only provider-confirmed terminal states release active reservations. Local clock expiry and lookup outages do not prove nonpayment. Amount/identifier mismatches, missing stock/reservations, duplicate transaction identifiers and partial refunds require review. Completed-payment storage failures roll back atomically and can be retried through verification without creating a second order. Refunds update payment/order settlement without automatic restocking.

Run reconciliation from `backend/` using the configured environment:

```powershell
..\.venv\Scripts\python.exe manage.py reconcile_khalti --limit 100
..\.venv\Scripts\python.exe manage.py reconcile_khalti --limit 100 --include-settled
```

The command uses real gateway lookup when configured. Operations must arrange periodic execution and monitor review cases before launch. Payments missing a provider identifier are reported for merchant investigation; do not release their reservations merely because a timeout elapsed. Resolve ambiguous provider records with Khalti support and the stored purchase-order UUID before making a controlled correction. There is no automatic refund initiation or manual staff settlement override.

## Real sandbox acceptance checks still required

With a valid merchant sandbox configuration, exercise success, cancellation, pending/recheck and an expired browser session. Confirm the provider reference and amount against the merchant dashboard, the paid order's snapshot, stock deduction and selected-only cart cleanup. Refresh/repeat the return URL and confirm the same order is shown. Record actual results separately from contract-test results; sandbox completion does not establish live-payment readiness.

Automated payment coverage lives in `backend/commerce/test_payments.py` and the `test_commerce_khalti_*` browser cases. All database fixtures are confined to Django's disposable test database.
