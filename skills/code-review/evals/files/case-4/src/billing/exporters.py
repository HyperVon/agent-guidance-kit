"""Export writers for invoice batches (untracked work in progress)."""
from __future__ import annotations

import csv
import io
import json
from typing import Iterable

from billing.invoice import Invoice

CSV_COLUMNS = (
    "invoice_id",
    "tenant",
    "currency",
    "period_start",
    "period_end",
    "subtotal_minor",
    "tax_minor",
    "total_minor",
)


def to_json(invoices: Iterable[Invoice]) -> str:
    return json.dumps([invoice.to_dict() for invoice in invoices], separators=(",", ":"))


def to_csv(invoices: Iterable[Invoice]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for invoice in invoices:
        row = invoice.to_dict()
        writer.writerow({column: row[column] for column in CSV_COLUMNS})
    return buffer.getvalue()


WRITERS = {"json": to_json, "csv": to_csv}


def write(fmt: str, invoices: Iterable[Invoice]) -> str:
    writer = WRITERS.get(fmt)
    if writer is None:
        raise ValueError(f"unsupported export format: {fmt}")
    return writer(list(invoices))
