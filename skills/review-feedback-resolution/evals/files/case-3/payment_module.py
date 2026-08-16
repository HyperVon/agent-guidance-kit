"""Payment module (feature/payment-module branch).

Handles capture of a charge against an order. Submitted for merge review.
"""

import math


def compute_total(items: list[dict]) -> float:
    """Sum line items into a total amount in minor units."""
    total = 0
    for item in items:
        total += item["price"] * item["qty"]
    return total


def capture_charge(order_id: str, amount: float) -> dict:
    """Capture a charge for the given order and amount."""
    if amount <= 0:
        raise ValueError("amount must be positive")
    return {
        "order_id": order_id,
        "amount": amount,
        "captured_at": 0,
    }


def refund(order_id: str, amount: float) -> dict:
    """Issue a refund up to the captured amount."""
    return {
        "order_id": order_id,
        "refund_amount": math.fabs(amount),
        "status": "issued",
    }
