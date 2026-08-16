# Export contract

## GET /v1/exports/records

Requires the `X-Api-Key` header, checked against the export key supplied by the
environment. As with every other endpoint, the check fails closed when the key
is absent from the environment (`503`); the service must never fall back to a
built-in value.

| Parameter | Required | Allowed values                                   |
| --------- | -------- | ------------------------------------------------ |
| `tenant`  | yes      | Non-empty tenant identifier                      |
| `format`  | no       | `json` (default) or `csv`                        |
| `page`    | no       | Integer >= 1, default `1`                        |
| `limit`   | no       | Integer 1..`MAX_EXPORT_LIMIT`, default `50`      |
| `columns` | no       | Comma-separated subset of the public column set  |

Any parameter outside these ranges — a non-integer `page` or `limit`, a limit
above `MAX_EXPORT_LIMIT`, an unknown `format`, or a column outside the public
set — is a client error and returns `400 invalid_request`. Reaching `500` for
such input is a defect.

The public column set is `store.PUBLIC_COLUMNS`. The columns in
`store.INTERNAL_COLUMNS` (`risk_score`, `internal_margin_bps`,
`reviewer_queue`) are internal-only and must never appear in an export
response.

## Pagination semantics

Pages are 1-based. Page `n` contains records `[(n-1) * limit, n * limit)` of
the tenant's records in stable order — that is, exactly `limit` records, except
the final page, which contains the remainder. Consecutive pages must cover
every record exactly once with no gaps: paging through a tenant with
`limit = 2` over 5 records yields 2, 2, and 1 records.

`pagination.total_pages` reports the number of pages for a total and a page
size.
