"""HTTP surface for the billing service."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Blueprint, Response, jsonify, request

from billing import exporters, invoice as invoice_module, rounding
from billing.repository import find_invoices, find_one_invoice

logger = logging.getLogger(__name__)

api = Blueprint("billing", __name__)


@api.get("/v1/invoices/<invoice_id>")
def get_invoice(invoice_id: str):
    record = find_one_invoice(invoice_id)
    if record is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify(record.to_dict()), 200


@api.get("/v1/invoices/export")
def export_invoices():
    fmt = request.args.get("format", "json")
    tenant = request.args.get("tenant")
    if not tenant:
        return jsonify({"error": "invalid_request", "detail": "tenant"}), 400
    records = find_invoices(tenant=tenant)
    try:
        body = exporters.write(fmt, records)
    except ValueError as exc:
        return jsonify({"error": "invalid_request", "detail": str(exc)}), 400
    content_type = "text/csv" if fmt == "csv" else "application/json"
    return Response(body, content_type=content_type), 200


@api.post("/v1/invoices/preview-proration")
def preview_proration():
    payload = request.get_json(silent=True) or {}
    try:
        amount_minor = int(payload["amount_minor"])
        changed_at = datetime.fromisoformat(payload["changed_at"])
        period_start = datetime.fromisoformat(payload["period_start"])
        period_end = datetime.fromisoformat(payload["period_end"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "invalid_request"}), 400

    prorated = rounding.prorate_upgrade(
        amount_minor=amount_minor,
        currency=payload.get("currency", "USD"),
        changed_at=changed_at,
        period_start=period_start,
        period_end=period_end,
        tenant_timezone=payload.get("tenant_timezone", "UTC"),
    )
    return jsonify({"prorated_minor": prorated, "computed_at": datetime.now(timezone.utc).isoformat()}), 200
