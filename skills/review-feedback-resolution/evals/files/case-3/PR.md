# Pull Request — payment module

Branch: `feature/payment-module`
Base: `main`
Diff range: `main...feature/payment-module`

This is a brand-new module with no prior review comments. The author is asking
for a review to find bugs or defects before merge.

There are no reviewer comments yet — the request is to *discover* issues in the
diff below, not to resolve existing feedback.

## Diff (new file: payment_module.py)

The full module is attached as `payment_module.py`. Notable areas a reviewer
would inspect:

- `compute_total` iterates items but never rounds; floating-point sums can drift
  for currency values.
- `capture_charge` records `captured_at: 0` instead of the actual capture
  timestamp.
- `refund` applies `math.fabs` to the amount, silently turning negative
  refund requests into positive ones (a caller error becomes a payout).
