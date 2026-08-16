# Invoice export contract (draft)

Status: draft — endpoint on `feature/invoice-export`, not yet released.

## GET /v1/invoices/export

Query parameters:

| Name     | Required | Notes                                  |
| -------- | -------- | -------------------------------------- |
| `tenant` | yes      | Restricts export to one tenant         |
| `format` | no       | `json` (default) or `csv`              |

Responses:

- `200` with `application/json` or `text/csv` body
- `400` `{ "error": "invalid_request" }` for a missing tenant or unknown format

## Open items

- No pagination; a large tenant returns everything in one response.
- CSV column set is fixed in `exporters.CSV_COLUMNS`; line items are not
  included in CSV, only invoice-level totals.
- Authorization for this endpoint has not been wired up in this draft.
