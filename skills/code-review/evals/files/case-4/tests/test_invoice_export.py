from __future__ import annotations

import json
from datetime import datetime, timezone

from billing import exporters
from billing.invoice import Invoice, LineItem


def _invoice(invoice_id="inv_2001", tenant="acme", currency="USD"):
    return Invoice(
        invoice_id=invoice_id,
        tenant=tenant,
        currency=currency,
        period_start=datetime(2024, 6, 1, tzinfo=timezone.utc),
        period_end=datetime(2024, 7, 1, tzinfo=timezone.utc),
        lines=[LineItem("Team plan", 2, 2500, currency)],
        tax_rate_bps=0,
    )


def test_to_json_returns_a_string():
    result = exporters.to_json([_invoice()])
    assert isinstance(result, str)


def test_to_json_is_valid_json():
    result = exporters.to_json([_invoice()])
    assert json.loads(result) is not None


def test_to_json_contains_invoice_id():
    result = exporters.to_json([_invoice()])
    assert "inv_2001" in result


def test_to_json_handles_empty_list():
    assert exporters.to_json([]) == "[]"


def test_to_csv_returns_a_string():
    result = exporters.to_csv([_invoice()])
    assert isinstance(result, str)


def test_to_csv_has_a_header_row():
    result = exporters.to_csv([_invoice()])
    assert result.splitlines()[0] == ",".join(exporters.CSV_COLUMNS)


def test_to_csv_contains_the_tenant():
    result = exporters.to_csv([_invoice()])
    assert "acme" in result


def test_to_csv_handles_empty_list():
    result = exporters.to_csv([])
    assert result.strip() == ",".join(exporters.CSV_COLUMNS)


def test_write_dispatches_json():
    assert exporters.write("json", [_invoice()]) == exporters.to_json([_invoice()])


def test_write_dispatches_csv():
    assert exporters.write("csv", [_invoice()]) == exporters.to_csv([_invoice()])


def test_write_rejects_unknown_format():
    try:
        exporters.write("xml", [_invoice()])
        assert False
    except ValueError:
        assert True


def test_writers_registry_is_a_dict():
    assert isinstance(exporters.WRITERS, dict)


def test_writers_registry_has_two_entries():
    assert len(exporters.WRITERS) == 2


def test_csv_columns_is_a_tuple():
    assert isinstance(exporters.CSV_COLUMNS, tuple)


def test_csv_columns_has_eight_entries():
    assert len(exporters.CSV_COLUMNS) == 8
