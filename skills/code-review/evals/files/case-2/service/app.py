"""HTTP surface for the payments gateway."""
from __future__ import annotations

import logging

from flask import Blueprint, Flask, jsonify, request

import auth
import ledger
import settings
import token as token_helper
from errors import AuthRejected, IssuanceRejected

logger = logging.getLogger(__name__)

api = Blueprint("api", __name__)


@api.get("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200


@api.post("/v1/tokens")
def create_token():
    """Internal-only issuance endpoint; reachable from the service mesh."""
    if request.headers.get("X-Mesh-Client") not in settings.MESH_CLIENTS:
        return jsonify({"error": "forbidden"}), 403
    payload = request.get_json(silent=True) or {}
    try:
        issued = token_helper.issue_access_token(
            subject=str(payload.get("subject", "")),
            tenant=str(payload.get("tenant", "default")),
            scopes=payload.get("scopes") or [],
            lifetime_seconds=payload.get("lifetime_seconds"),
        )
    except IssuanceRejected as exc:
        return jsonify({"error": "issuance_rejected", "detail": str(exc)}), 400
    return jsonify({"access_token": issued, "token_type": "Bearer"}), 201


@api.get("/v1/payments")
def list_payments():
    try:
        principal = auth.require_scope(dict(request.headers), "payments:read")
    except AuthRejected as exc:
        return jsonify({"error": exc.code}), exc.status
    return jsonify({"payments": ledger.list_payments(principal.tenant)}), 200


@api.post("/v1/refunds")
def create_refund():
    try:
        principal = auth.require_scope(dict(request.headers), "refunds:write")
    except AuthRejected as exc:
        return jsonify({"error": exc.code}), exc.status
    payload = request.get_json(silent=True) or {}
    amount_minor = payload.get("amount_minor")
    if not isinstance(amount_minor, int) or amount_minor <= 0:
        return jsonify({"error": "invalid_request", "detail": "amount_minor"}), 400
    refund = ledger.create_refund(
        tenant=principal.tenant,
        actor=principal.subject,
        payment_id=str(payload.get("payment_id", "")),
        amount_minor=amount_minor,
    )
    return jsonify(refund), 201


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(api)
    logging.basicConfig(level=settings.LOG_LEVEL)
    return app
