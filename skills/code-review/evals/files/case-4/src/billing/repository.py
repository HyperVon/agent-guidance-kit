"""In-memory stand-in for the invoice repository used in local runs."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from billing.invoice import Invoice, LineItem

_PERIOD_START = datetime(2024, 6, 1, tzinfo=timezone.utc)
_PERIOD_END = datetime(2024, 7, 1, tzinfo=timezone.utc)

_INVOICES = [
    Invoice(
        invoice_id="inv_1001",
        tenant="acme",
        currency="USD",
        period_start=_PERIOD_START,
        period_end=_PERIOD_END,
        lines=[LineItem("Team plan", 12, 2500, "USD"), LineItem("Overage", 3, 400, "USD")],
        tax_rate_bps=875,
    ),
    Invoice(
        invoice_id="inv_1002",
        tenant="acme",
        currency="USD",
        period_start=_PERIOD_START,
        period_end=_PERIOD_END,
        lines=[LineItem("Team plan", 4, 2500, "USD")],
        tax_rate_bps=0,
    ),
    Invoice(
        invoice_id="inv_1003",
        tenant="globex",
        currency="EUR",
        period_start=_PERIOD_START,
        period_end=_PERIOD_END,
        lines=[LineItem("Enterprise plan", 1, 480000, "EUR")],
        tax_rate_bps=2100,
    ),
]


def find_invoices(tenant: Optional[str] = None) -> list[Invoice]:
    if tenant is None:
        return list(_INVOICES)
    return [inv for inv in _INVOICES if inv.tenant == tenant]


def find_one_invoice(invoice_id: str) -> Optional[Invoice]:
    for invoice in _INVOICES:
        if invoice.invoice_id == invoice_id:
            return invoice
    return None
