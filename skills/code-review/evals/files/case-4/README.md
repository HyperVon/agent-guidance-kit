# Meadowlark billing

Billing and invoicing service for the subscription product. Python service,
plus a small internal admin UI under `admin-ui/`.

## Layout

| Path                       | Purpose                                       |
| -------------------------- | --------------------------------------------- |
| `src/api/routes.py`        | HTTP surface                                  |
| `src/billing/invoice.py`   | Invoice assembly and export                   |
| `src/billing/rounding.py`  | Currency rounding and proration                |
| `src/billing/dunning.py`   | Retry schedule for failed charges              |
| `src/billing/exporters.py` | CSV/JSON export writers                        |
| `admin-ui/src/`            | Internal admin console (TypeScript)            |
| `patches/`                 | Exported diffs for the in-flight branches      |
| `tests/`                   | pytest suite                                   |
| `docs/`                    | Contracts, review conventions, release notes   |
| `notes/handoff.md`         | Current state of work in progress              |

## Local checks

```
pip install -r requirements.txt
PYTHONPATH=src python -m pytest -q
cd admin-ui && npm test
```

## Current state

Several changes are in flight at once (see `notes/handoff.md` and
`git-state.txt`). The working tree also has uncommitted edits.
