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
