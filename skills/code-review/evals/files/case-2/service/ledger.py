"""Ledger reads and refund writes (trimmed for the review snapshot)."""
from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

_PAYMENTS: dict[str, list[dict[str, Any]]] = {
    "default": [
        {"payment_id": "pay_2f81", "amount_minor": 4500, "currency": "USD", "state": "captured"},
        {"payment_id": "pay_9c02", "amount_minor": 19900, "currency": "USD", "state": "captured"},
    ],
    "acme": [
        {"payment_id": "pay_4d17", "amount_minor": 250000, "currency": "EUR", "state": "captured"},
    ],
}


def list_payments(tenant: str) -> list[dict[str, Any]]:
    return list(_PAYMENTS.get(tenant, []))


def find_payment(tenant: str, payment_id: str) -> dict[str, Any] | None:
    for payment in _PAYMENTS.get(tenant, []):
        if payment["payment_id"] == payment_id:
            return payment
    return None


def create_refund(tenant: str, actor: str, payment_id: str, amount_minor: int) -> dict[str, Any]:
    payment = find_payment(tenant, payment_id)
    if payment is None:
        raise ValueError("payment not found for tenant")
    if amount_minor > payment["amount_minor"]:
        raise ValueError("refund exceeds captured amount")
    refund_id = "rfnd_" + uuid.uuid4().hex[:8]
    logger.info(
        "refund created tenant=%s actor=%s payment=%s amount_minor=%s",
        tenant,
        actor,
        payment_id,
        amount_minor,
    )
    return {
        "refund_id": refund_id,
        "payment_id": payment_id,
        "amount_minor": amount_minor,
        "state": "pending",
    }
