# Handoff notes

Everything below is open at the same time. Nothing here is finished.

## 1. Proration rounding in tenant timezone (`fix/timezone-rounding`)

Currently checked out. A customer in a UTC+13 tenant was billed for an extra
day on an upgrade. `rounding.py` has an uncommitted edit on top of the branch
commit; the branch has also diverged from its remote (1 ahead, 1 behind) after
a force-push from another machine.

Open question: whether proration boundaries should be computed in the tenant
timezone or in the billing-account timezone. The two differ for 41 accounts.

## 2. Invoice export endpoint (`feature/invoice-export`)

Three commits, pushed. Adds `GET /v1/invoices/export`. The exporter writers
(`src/billing/exporters.py`) are still untracked in the working tree, so the
branch and the working tree disagree about what "export" means right now.

Test file `tests/test_invoice_export.py` was drafted quickly and has not been
reviewed by anyone.

## 3. Dependency bumps (`chore/bump-deps`)

One commit. Bumps runtime and dev dependencies. `pytest` and the CSV writer
library both changed major versions. Nobody has run the suite against it yet.

## 4. Ledger spike (`spike/ledger-rewrite`)

Exploratory only. Marked "do not review" in the commit message; kept around
for the architecture discussion.

## 5. Admin console invoice table

`admin-ui/src/InvoiceTable.tsx` has an uncommitted change to the sorting and
currency display. It has no test coverage yet.

## 6. Dunning retry cap

Landed on `main` last week (`c17e330`) but the follow-up review comments were
never addressed and the file has since picked up an uncommitted edit.
