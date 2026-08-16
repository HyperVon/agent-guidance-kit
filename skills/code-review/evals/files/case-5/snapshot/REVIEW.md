# Review of feature/export-endpoint

Reviewer: platform on-call
Base: `main` (merge base `main`..`feature/export-endpoint`)
Scope: the export endpoint commit on this branch
Checks run by the reviewer: `make test` on the branch tip (passing)

## Findings

### P1-1 — Export route accepts unvalidated query input

`app/export.py`, `handle_export`. `format`, `page`, `limit`, and `columns`
are taken from the query string and used without range or membership checks:

- `page` and `limit` go through bare `int(...)`, so a non-numeric value raises
  and the dispatcher turns it into `500`.
- `limit` has no upper bound even though `config.MAX_EXPORT_LIMIT` exists.
- `page` may be zero or negative, which produces a slice with negative
  indices instead of a client error.
- `format` indexes `WRITERS` and `CONTENT_TYPES` directly, so an unknown value
  raises instead of returning `400`.
- `columns` is split from the query string and passed straight to the writer,
  so a caller can name columns from `store.INTERNAL_COLUMNS` and receive
  internal fields.

Expected behavior is in `docs/export-format.md`: each of these is a
`400 invalid_request`, and internal columns must never be exported.

### P1-2 — Hardcoded key value in configuration

`app/config.py`, `EXPORT_API_KEY`. The export key falls back to a built-in
literal when `EXPORT_API_KEY` is absent from the environment, and
`app/auth.py`, `require_export_key` compares the caller-supplied header
against it. Any deployment that has not set the variable accepts the built-in
value. `config.api_key` in the same module shows the intended pattern: fail
closed when the variable is missing, and let the caller map that to `503`
(`docs/api.md`, `docs/export-format.md`).

### P1-3 — Off-by-one in the pagination bounds

`app/pagination.py`, `page_slice`. The end bound is computed as
`start + size - 1`, so each page returns `size - 1` records and one record per
page is skipped. `docs/export-format.md` specifies page `n` as
`[(n-1) * limit, n * limit)`, with consecutive pages covering every record
exactly once. `total_pages` is consistent with the documented semantics, so
the two helpers currently disagree with each other.

The existing tests in `tests/test_pagination.py` do not catch this: they only
exercise an empty input and a page size larger than the input, where the
buggy and correct bounds agree.

## Not findings

- `tenant` is validated before use in `handle_export`.
- `require_api_key` keeps the constant-time comparison and the fail-closed
  `503` path from `main`.
- The `csv` writer quotes values through the `csv` module rather than by hand.
- `total_pages` rejects a non-positive page size.

## Verification gaps

- No test covers a multi-page export end to end.
- The export route has not been exercised against a large tenant, so the
  effect of an unbounded `limit` on memory is unmeasured.
