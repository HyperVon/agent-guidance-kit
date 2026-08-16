"""Invoice assembly."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Iterable

from billing import rounding

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LineItem:
    description: str
    quantity: int
    unit_amount_minor: int
    currency: str

    @property
    def subtotal_minor(self) -> int:
        return self.quantity * self.unit_amount_minor


@dataclass
class Invoice:
    invoice_id: str
    tenant: str
    currency: str
    period_start: datetime
    period_end: datetime
    lines: list[LineItem] = field(default_factory=list)
    tax_rate_bps: int = 0

    @property
    def subtotal_minor(self) -> int:
        return sum(line.subtotal_minor for line in self.lines)

    @property
    def tax_minor(self) -> int:
        return rounding.to_minor(
            Decimal(self.subtotal_minor) * Decimal(self.tax_rate_bps) / Decimal(10000),
            "JPY",
        )

    @property
    def total_minor(self) -> int:
        return self.subtotal_minor + self.tax_minor

    def to_dict(self) -> dict:
        return {
            "invoice_id": self.invoice_id,
            "tenant": self.tenant,
            "currency": self.currency,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "subtotal_minor": self.subtotal_minor,
            "tax_minor": self.tax_minor,
            "total_minor": self.total_minor,
            "lines": [
                {
                    "description": line.description,
                    "quantity": line.quantity,
                    "unit_amount_minor": line.unit_amount_minor,
                }
                for line in self.lines
            ],
        }


def assemble(
    invoice_id: str,
    tenant: str,
    currency: str,
    period_start: datetime,
    period_end: datetime,
    lines: Iterable[LineItem],
    tax_rate_bps: int = 0,
) -> Invoice:
    invoice = Invoice(
        invoice_id=invoice_id,
        tenant=tenant,
        currency=currency,
        period_start=period_start,
        period_end=period_end,
        lines=list(lines),
        tax_rate_bps=tax_rate_bps,
    )
    mismatched = [line for line in invoice.lines if line.currency != currency]
    if mismatched:
        raise ValueError(f"line currency mismatch: {[l.description for l in mismatched]}")
    logger.info(
        "invoice assembled id=%s tenant=%s lines=%d", invoice_id, tenant, len(invoice.lines)
    )
    return invoice
