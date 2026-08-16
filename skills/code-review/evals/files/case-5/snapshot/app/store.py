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
