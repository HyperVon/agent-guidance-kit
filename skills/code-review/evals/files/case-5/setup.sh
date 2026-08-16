#!/usr/bin/env bash
#
# Deterministic fixture generator: builds a small git repository for a review
# exercise on branch feature/export-endpoint.
#
# Usage: run from an empty directory
#
#   mkdir -p /tmp/case-5 && cd /tmp/case-5
#   bash /path/to/setup.sh
#
# The generator never touches global or user git configuration: the commit
# identity is passed per invocation with `git -c`.

set -euo pipefail

if [ -e .git ]; then
  echo "refusing to run: .git already exists in $(basename "$PWD")" >&2
  exit 1
fi

# Fixture-local commit identity. Not a real person or account.
GIT_ID=(-c "user.name=Eval Bot" -c "user.email=eval@example.com" -c commit.gpgsign=false)

git init -q .
git symbolic-ref HEAD refs/heads/main

mkdir -p app tests docs

# ---------------------------------------------------------------------------
# Baseline commit on main
# ---------------------------------------------------------------------------

cat > README.md <<'EOF'
# Reporting API

Internal reporting service for tenant transaction records. Standard library
only: no third-party runtime or test dependencies.

## Layout

| Path                 | Purpose                                        |
| -------------------- | ---------------------------------------------- |
| `app/router.py`      | Request/response plumbing and dispatch         |
| `app/config.py`      | Environment configuration                      |
| `app/store.py`       | Record source (in-memory for local runs)       |
| `app/auth.py`        | API key checks                                 |
| `app/reports.py`     | Summary endpoints                              |
| `app/main.py`        | Route registration                             |
| `docs/api.md`        | Endpoint contract                              |
| `tests/`             | unittest suite                                 |

## Checks

```
make test
```

or directly:

```
python3 -m unittest discover -s tests -t .
```
EOF

cat > Makefile <<'EOF'
.PHONY: test
test:
	python3 -m unittest discover -s tests -t .
EOF

cat > app/__init__.py <<'EOF'
"""Reporting API application package."""
EOF

cat > app/router.py <<'EOF'
"""Minimal request/response plumbing and dispatch."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    query: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_url(cls, method: str, url: str, headers: Optional[Dict[str, str]] = None) -> "Request":
        parsed = urlparse(url)
        query = {
            key: values[-1]
            for key, values in parse_qs(parsed.query, keep_blank_values=True).items()
        }
        return cls(
            method=method.upper(),
            path=parsed.path,
            query=query,
            headers={k: v for k, v in (headers or {}).items()},
        )


@dataclass(frozen=True)
class Response:
    status: int
    body: str = ""
    content_type: str = "application/json"

    @classmethod
    def error(cls, status: int, code: str, detail: Optional[str] = None) -> "Response":
        payload = {"error": code}
        if detail:
            payload["detail"] = detail
        return cls(status=status, body=json.dumps(payload), content_type="application/json")


class Router:
    def __init__(self) -> None:
        self._routes: Dict[tuple, Callable[[Request], Response]] = {}

    def add(self, method: str, path: str, handler: Callable[[Request], Response]) -> None:
        self._routes[(method.upper(), path)] = handler

    def dispatch(self, request: Request) -> Response:
        handler = self._routes.get((request.method, request.path))
        if handler is None:
            return Response.error(404, "not_found")
        try:
            return handler(request)
        except Exception:
            logger.exception("unhandled error serving %s %s", request.method, request.path)
            return Response.error(500, "internal_error")

    @property
    def routes(self) -> tuple:
        return tuple(sorted(self._routes))
EOF

cat > app/config.py <<'EOF'
"""Environment configuration. No secret values are committed."""
from __future__ import annotations

import os

SERVICE_NAME = "reporting-api"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

DEFAULT_PAGE_SIZE = int(os.environ.get("DEFAULT_PAGE_SIZE", "50"))
MAX_EXPORT_LIMIT = int(os.environ.get("MAX_EXPORT_LIMIT", "500"))


def api_key() -> str:
    """Return the reporting API key, or fail closed when it is not configured."""
    value = os.environ.get("REPORTING_API_KEY")
    if not value:
        raise RuntimeError("REPORTING_API_KEY is not configured")
    return value
EOF

cat > app/store.py <<'EOF'
"""Record source. Backed by an in-memory dataset for local runs and tests."""
from __future__ import annotations

from typing import Dict, List

PUBLIC_COLUMNS = ("record_id", "tenant", "amount_minor", "currency", "captured_at", "state")
INTERNAL_COLUMNS = ("risk_score", "internal_margin_bps", "reviewer_queue")

_RECORDS: List[Dict[str, object]] = [
    {
        "record_id": "rec_0001",
        "tenant": "acme",
        "amount_minor": 12500,
        "currency": "USD",
        "captured_at": "2024-06-01T10:15:00Z",
        "state": "captured",
        "risk_score": 12,
        "internal_margin_bps": 220,
        "reviewer_queue": "standard",
    },
    {
        "record_id": "rec_0002",
        "tenant": "acme",
        "amount_minor": 4200,
        "currency": "USD",
        "captured_at": "2024-06-01T11:02:00Z",
        "state": "captured",
        "risk_score": 71,
        "internal_margin_bps": 180,
        "reviewer_queue": "manual",
    },
    {
        "record_id": "rec_0003",
        "tenant": "acme",
        "amount_minor": 98000,
        "currency": "USD",
        "captured_at": "2024-06-02T08:44:00Z",
        "state": "refunded",
        "risk_score": 33,
        "internal_margin_bps": 260,
        "reviewer_queue": "standard",
    },
    {
        "record_id": "rec_0004",
        "tenant": "acme",
        "amount_minor": 15000,
        "currency": "USD",
        "captured_at": "2024-06-02T09:30:00Z",
        "state": "captured",
        "risk_score": 8,
        "internal_margin_bps": 205,
        "reviewer_queue": "standard",
    },
    {
        "record_id": "rec_0005",
        "tenant": "acme",
        "amount_minor": 760,
        "currency": "USD",
        "captured_at": "2024-06-03T14:05:00Z",
        "state": "captured",
        "risk_score": 44,
        "internal_margin_bps": 190,
        "reviewer_queue": "standard",
    },
    {
        "record_id": "rec_0101",
        "tenant": "globex",
        "amount_minor": 480000,
        "currency": "EUR",
        "captured_at": "2024-06-01T07:10:00Z",
        "state": "captured",
        "risk_score": 19,
        "internal_margin_bps": 310,
        "reviewer_queue": "standard",
    },
    {
        "record_id": "rec_0102",
        "tenant": "globex",
        "amount_minor": 22000,
        "currency": "EUR",
        "captured_at": "2024-06-04T16:20:00Z",
        "state": "captured",
        "risk_score": 55,
        "internal_margin_bps": 275,
        "reviewer_queue": "manual",
    },
]


def all_records() -> List[Dict[str, object]]:
    return [dict(record) for record in _RECORDS]


def records_for_tenant(tenant: str) -> List[Dict[str, object]]:
    return [dict(record) for record in _RECORDS if record["tenant"] == tenant]


def tenants() -> List[str]:
    return sorted({str(record["tenant"]) for record in _RECORDS})
EOF

cat > app/auth.py <<'EOF'
"""API key checks for the reporting endpoints."""
from __future__ import annotations

import hmac
from typing import Optional

from app import config
from app.router import Request, Response

API_KEY_HEADER = "X-Api-Key"


def require_api_key(request: Request) -> Optional[Response]:
    """Return an error response when the request is not authorized."""
    provided = request.headers.get(API_KEY_HEADER, "")
    if not provided:
        return Response.error(401, "unauthorized")
    try:
        expected = config.api_key()
    except RuntimeError:
        return Response.error(503, "api_key_not_configured")
    if not hmac.compare_digest(provided, expected):
        return Response.error(401, "unauthorized")
    return None
EOF

cat > app/reports.py <<'EOF'
"""Summary report endpoints."""
from __future__ import annotations

import json
import logging

from app import store
from app.auth import require_api_key
from app.router import Request, Response

logger = logging.getLogger(__name__)


def handle_tenant_summary(request: Request) -> Response:
    denied = require_api_key(request)
    if denied is not None:
        return denied

    tenant = request.query.get("tenant", "").strip()
    if not tenant:
        return Response.error(400, "invalid_request", "tenant is required")
    if tenant not in store.tenants():
        return Response.error(404, "not_found")

    records = store.records_for_tenant(tenant)
    captured = [r for r in records if r["state"] == "captured"]
    body = {
        "tenant": tenant,
        "record_count": len(records),
        "captured_count": len(captured),
        "captured_total_minor": sum(int(r["amount_minor"]) for r in captured),
        "currency": captured[0]["currency"] if captured else None,
    }
    logger.info("summary served tenant=%s records=%d", tenant, len(records))
    return Response(200, json.dumps(body))


def handle_tenant_list(request: Request) -> Response:
    denied = require_api_key(request)
    if denied is not None:
        return denied
    return Response(200, json.dumps({"tenants": store.tenants()}))
EOF

cat > app/main.py <<'EOF'
"""Route registration."""
from __future__ import annotations

import logging

from app import config, reports
from app.router import Router


def build_router() -> Router:
    logging.basicConfig(level=config.LOG_LEVEL)
    router = Router()
    router.add("GET", "/v1/tenants", reports.handle_tenant_list)
    router.add("GET", "/v1/reports/summary", reports.handle_tenant_summary)
    return router
EOF

cat > docs/api.md <<'EOF'
# Endpoint contract

All endpoints require the `X-Api-Key` header. A missing or mismatched key
returns `401`. When the key is not configured in the environment, the service
returns `503` rather than serving the request: authorization checks fail
closed.

## GET /v1/tenants

Returns `{ "tenants": [...] }`.

## GET /v1/reports/summary

| Parameter | Required | Notes                     |
| --------- | -------- | ------------------------- |
| `tenant`  | yes      | Unknown tenant gives `404` |

Returns record counts and the captured total in minor units.

## Error shape

```json
{ "error": "invalid_request", "detail": "tenant is required" }
```

Client input problems are `400`. An unexpected server error is `500` and is
logged with a traceback; reaching `500` from ordinary client input is a defect.
EOF

cat > tests/__init__.py <<'EOF'
EOF

cat > tests/test_router.py <<'EOF'
import json
import unittest

from app.router import Request, Response, Router


class RequestParsingTests(unittest.TestCase):
    def test_parses_path_and_query(self):
        request = Request.from_url("get", "/v1/reports/summary?tenant=acme&limit=10")
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.path, "/v1/reports/summary")
        self.assertEqual(request.query["tenant"], "acme")
        self.assertEqual(request.query["limit"], "10")

    def test_keeps_blank_values(self):
        request = Request.from_url("GET", "/v1/reports/summary?tenant=")
        self.assertEqual(request.query["tenant"], "")


class DispatchTests(unittest.TestCase):
    def test_unknown_route_returns_404(self):
        router = Router()
        response = router.dispatch(Request.from_url("GET", "/nope"))
        self.assertEqual(response.status, 404)
        self.assertEqual(json.loads(response.body)["error"], "not_found")

    def test_handler_exception_becomes_500(self):
        router = Router()

        def boom(request):
            raise RuntimeError("boom")

        router.add("GET", "/boom", boom)
        with self.assertLogs("app.router", level="ERROR"):
            response = router.dispatch(Request.from_url("GET", "/boom"))
        self.assertEqual(response.status, 500)

    def test_error_response_includes_detail(self):
        response = Response.error(400, "invalid_request", "tenant is required")
        self.assertEqual(json.loads(response.body)["detail"], "tenant is required")
EOF

cat > tests/test_auth.py <<'EOF'
import os
import unittest

from app.auth import require_api_key
from app.router import Request


class ApiKeyTests(unittest.TestCase):
    def setUp(self):
        self._previous = os.environ.get("REPORTING_API_KEY")
        os.environ["REPORTING_API_KEY"] = "test-key-value"

    def tearDown(self):
        if self._previous is None:
            os.environ.pop("REPORTING_API_KEY", None)
        else:
            os.environ["REPORTING_API_KEY"] = self._previous

    def test_missing_header_is_rejected(self):
        response = require_api_key(Request.from_url("GET", "/v1/tenants"))
        self.assertIsNotNone(response)
        self.assertEqual(response.status, 401)

    def test_wrong_key_is_rejected(self):
        request = Request.from_url("GET", "/v1/tenants", headers={"X-Api-Key": "wrong"})
        response = require_api_key(request)
        self.assertEqual(response.status, 401)

    def test_matching_key_is_accepted(self):
        request = Request.from_url("GET", "/v1/tenants", headers={"X-Api-Key": "test-key-value"})
        self.assertIsNone(require_api_key(request))

    def test_unconfigured_key_fails_closed(self):
        os.environ.pop("REPORTING_API_KEY", None)
        request = Request.from_url("GET", "/v1/tenants", headers={"X-Api-Key": "anything"})
        response = require_api_key(request)
        self.assertEqual(response.status, 503)
EOF

cat > tests/test_reports.py <<'EOF'
import json
import os
import unittest

from app.main import build_router
from app.router import Request

HEADERS = {"X-Api-Key": "test-key-value"}


class SummaryTests(unittest.TestCase):
    def setUp(self):
        os.environ["REPORTING_API_KEY"] = "test-key-value"
        self.router = build_router()

    def test_summary_requires_tenant(self):
        response = self.router.dispatch(
            Request.from_url("GET", "/v1/reports/summary", headers=HEADERS)
        )
        self.assertEqual(response.status, 400)

    def test_unknown_tenant_is_404(self):
        response = self.router.dispatch(
            Request.from_url("GET", "/v1/reports/summary?tenant=nope", headers=HEADERS)
        )
        self.assertEqual(response.status, 404)

    def test_summary_totals_only_captured_records(self):
        response = self.router.dispatch(
            Request.from_url("GET", "/v1/reports/summary?tenant=acme", headers=HEADERS)
        )
        self.assertEqual(response.status, 200)
        body = json.loads(response.body)
        self.assertEqual(body["record_count"], 5)
        self.assertEqual(body["captured_count"], 4)
        self.assertEqual(body["captured_total_minor"], 32460)

    def test_tenant_list(self):
        response = self.router.dispatch(Request.from_url("GET", "/v1/tenants", headers=HEADERS))
        self.assertEqual(json.loads(response.body)["tenants"], ["acme", "globex"])
EOF

git "${GIT_ID[@]}" add -A
GIT_AUTHOR_DATE="2024-06-04T09:12:00+00:00" \
GIT_COMMITTER_DATE="2024-06-04T09:12:00+00:00" \
  git "${GIT_ID[@]}" commit -q -m "Reporting API: summary endpoints, router, api key checks"

# ---------------------------------------------------------------------------
# Feature branch
# ---------------------------------------------------------------------------

git "${GIT_ID[@]}" checkout -q -b feature/export-endpoint

cat > app/pagination.py <<'EOF'
"""Pagination helpers for list and export endpoints."""
from __future__ import annotations

from typing import List, Sequence, TypeVar

T = TypeVar("T")


def page_slice(rows: Sequence[T], page: int, size: int) -> List[T]:
    """Return the records that belong to `page` (1-based) for `size` per page."""
    start = (page - 1) * size
    end = start + size - 1
    return list(rows[start:end])


def total_pages(total: int, size: int) -> int:
    if size <= 0:
        raise ValueError("size must be positive")
    return (total + size - 1) // size


def page_meta(total: int, page: int, size: int) -> dict:
    return {
        "page": page,
        "size": size,
        "total_records": total,
        "total_pages": total_pages(total, size),
    }
EOF

cat > app/export.py <<'EOF'
"""Export endpoint for tenant transaction records."""
from __future__ import annotations

import csv
import io
import json
import logging

from app import pagination, store
from app.auth import require_export_key
from app.router import Request, Response

logger = logging.getLogger(__name__)

DEFAULT_COLUMNS = ("record_id", "tenant", "amount_minor", "currency", "captured_at")
CONTENT_TYPES = {"json": "application/json", "csv": "text/csv"}


def _rows_to_json(rows, columns) -> str:
    return json.dumps(
        [{column: row.get(column) for column in columns} for row in rows],
        separators=(",", ":"),
    )


def _rows_to_csv(rows, columns) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row.get(column, "") for column in columns])
    return buffer.getvalue()


WRITERS = {"json": _rows_to_json, "csv": _rows_to_csv}


def handle_export(request: Request) -> Response:
    denied = require_export_key(request)
    if denied is not None:
        return denied

    tenant = request.query.get("tenant", "").strip()
    if not tenant:
        return Response.error(400, "invalid_request", "tenant is required")

    export_format = request.query.get("format", "json")
    page = int(request.query.get("page", "1"))
    limit = int(request.query.get("limit", "50"))
    columns = tuple(request.query.get("columns", ",".join(DEFAULT_COLUMNS)).split(","))

    rows = store.records_for_tenant(tenant)
    page_rows = pagination.page_slice(rows, page, limit)
    body = WRITERS[export_format](page_rows, columns)

    logger.info(
        "export served tenant=%s format=%s page=%s rows=%d",
        tenant,
        export_format,
        page,
        len(page_rows),
    )
    return Response(200, body, content_type=CONTENT_TYPES[export_format])
EOF

cat > app/auth.py <<'EOF'
"""API key checks for the reporting endpoints."""
from __future__ import annotations

import hmac
from typing import Optional

from app import config
from app.router import Request, Response

API_KEY_HEADER = "X-Api-Key"


def require_api_key(request: Request) -> Optional[Response]:
    """Return an error response when the request is not authorized."""
    provided = request.headers.get(API_KEY_HEADER, "")
    if not provided:
        return Response.error(401, "unauthorized")
    try:
        expected = config.api_key()
    except RuntimeError:
        return Response.error(503, "api_key_not_configured")
    if not hmac.compare_digest(provided, expected):
        return Response.error(401, "unauthorized")
    return None


def require_export_key(request: Request) -> Optional[Response]:
    """Return an error response when the export request is not authorized."""
    provided = request.headers.get(API_KEY_HEADER, "")
    if not provided:
        return Response.error(401, "unauthorized")
    if not hmac.compare_digest(provided, config.EXPORT_API_KEY):
        return Response.error(401, "unauthorized")
    return None
EOF

cat > app/config.py <<'EOF'
"""Environment configuration. No secret values are committed."""
from __future__ import annotations

import os

SERVICE_NAME = "reporting-api"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

DEFAULT_PAGE_SIZE = int(os.environ.get("DEFAULT_PAGE_SIZE", "50"))
MAX_EXPORT_LIMIT = int(os.environ.get("MAX_EXPORT_LIMIT", "500"))

EXPORT_API_KEY = os.environ.get("EXPORT_API_KEY", "REPLACE_ME_API_KEY")


def api_key() -> str:
    """Return the reporting API key, or fail closed when it is not configured."""
    value = os.environ.get("REPORTING_API_KEY")
    if not value:
        raise RuntimeError("REPORTING_API_KEY is not configured")
    return value
EOF

cat > app/main.py <<'EOF'
"""Route registration."""
from __future__ import annotations

import logging

from app import config, export, reports
from app.router import Router


def build_router() -> Router:
    logging.basicConfig(level=config.LOG_LEVEL)
    router = Router()
    router.add("GET", "/v1/tenants", reports.handle_tenant_list)
    router.add("GET", "/v1/reports/summary", reports.handle_tenant_summary)
    router.add("GET", "/v1/exports/records", export.handle_export)
    return router
EOF

cat > docs/export-format.md <<'EOF'
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
EOF

cat > tests/test_pagination.py <<'EOF'
import unittest

from app import pagination


class TotalPagesTests(unittest.TestCase):
    def test_empty_set_has_no_pages(self):
        self.assertEqual(pagination.total_pages(0, 10), 0)

    def test_exact_multiple(self):
        self.assertEqual(pagination.total_pages(20, 10), 2)

    def test_partial_last_page(self):
        self.assertEqual(pagination.total_pages(21, 10), 3)

    def test_rejects_non_positive_size(self):
        with self.assertRaises(ValueError):
            pagination.total_pages(10, 0)


class PageSliceTests(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual(pagination.page_slice([], 1, 10), [])

    def test_single_page_fits_everything(self):
        rows = ["a", "b", "c"]
        self.assertEqual(pagination.page_slice(rows, 1, 10), rows)

    def test_returns_a_list(self):
        self.assertIsInstance(pagination.page_slice(("a", "b"), 1, 10), list)


class PageMetaTests(unittest.TestCase):
    def test_meta_reports_totals(self):
        meta = pagination.page_meta(total=5, page=2, size=2)
        self.assertEqual(meta["page"], 2)
        self.assertEqual(meta["size"], 2)
        self.assertEqual(meta["total_records"], 5)
        self.assertEqual(meta["total_pages"], 3)
EOF

cat > tests/test_export.py <<'EOF'
import json
import os
import unittest

from app import export
from app.main import build_router
from app.router import Request

HEADERS = {"X-Api-Key": "REPLACE_ME_API_KEY"}


class ExportTests(unittest.TestCase):
    def setUp(self):
        os.environ["REPORTING_API_KEY"] = "test-key-value"
        self.router = build_router()

    def _get(self, url, headers=HEADERS):
        return self.router.dispatch(Request.from_url("GET", url, headers=headers))

    def test_requires_api_key(self):
        response = self._get("/v1/exports/records?tenant=acme", headers={})
        self.assertEqual(response.status, 401)

    def test_requires_tenant(self):
        response = self._get("/v1/exports/records")
        self.assertEqual(response.status, 400)

    def test_json_export_returns_json_body(self):
        response = self._get("/v1/exports/records?tenant=acme&format=json")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, "application/json")
        self.assertIsInstance(json.loads(response.body), list)

    def test_csv_export_has_header_row(self):
        response = self._get("/v1/exports/records?tenant=acme&format=csv")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, "text/csv")
        first_line = response.body.splitlines()[0]
        self.assertEqual(first_line.split(","), list(export.DEFAULT_COLUMNS))
EOF

git "${GIT_ID[@]}" add -A
GIT_AUTHOR_DATE="2024-06-05T11:40:00+00:00" \
GIT_COMMITTER_DATE="2024-06-05T11:40:00+00:00" \
  git "${GIT_ID[@]}" commit -q -m "Add record export endpoint with pagination"

cat > REVIEW.md <<'EOF'
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
EOF

git "${GIT_ID[@]}" add REVIEW.md
GIT_AUTHOR_DATE="2024-06-05T15:05:00+00:00" \
GIT_COMMITTER_DATE="2024-06-05T15:05:00+00:00" \
  git "${GIT_ID[@]}" commit -q -m "Add review notes for the export endpoint"

echo "fixture ready on branch $(git rev-parse --abbrev-ref HEAD)"
git "${GIT_ID[@]}" --no-pager log --oneline --decorate -3
