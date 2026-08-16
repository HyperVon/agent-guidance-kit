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
