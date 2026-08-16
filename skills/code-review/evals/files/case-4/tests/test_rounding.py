from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from billing import rounding


def test_split_evenly_sums_to_total():
    parts = rounding.split_evenly(1000, 3)
    assert sum(parts) == 1000
    assert parts == [334, 333, 333]


def test_split_evenly_rejects_zero_parts():
    with pytest.raises(ValueError):
        rounding.split_evenly(100, 0)


def test_to_minor_respects_currency_scale():
    assert rounding.to_minor(Decimal("12.345"), "USD") == 1235
    assert rounding.to_minor(Decimal("12.345"), "JPY") == 12
    assert rounding.to_minor(Decimal("12.3456"), "BHD") == 12346


def test_proration_factor_at_period_edges():
    start = datetime(2024, 6, 1, tzinfo=timezone.utc)
    end = datetime(2024, 7, 1, tzinfo=timezone.utc)

    assert rounding.proration_factor(start, start, end) == Decimal(1)
    assert rounding.proration_factor(end, start, end) == Decimal(0)


def test_proration_factor_rejects_out_of_period():
    start = datetime(2024, 6, 1, tzinfo=timezone.utc)
    end = datetime(2024, 7, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        rounding.proration_factor(datetime(2024, 5, 31, tzinfo=timezone.utc), start, end)


def test_proration_boundary_in_positive_offset_tenant():
    start = datetime(2024, 6, 1, tzinfo=timezone.utc)
    end = datetime(2024, 7, 1, tzinfo=timezone.utc)
    # Upgrade at 2024-06-15T20:00Z is already 2024-06-16 local in UTC+13.
    changed_at = datetime(2024, 6, 15, 20, 0, tzinfo=timezone.utc)

    prorated = rounding.prorate_upgrade(
        amount_minor=30000,
        currency="USD",
        changed_at=changed_at,
        period_start=start,
        period_end=end,
        tenant_timezone="Pacific/Auckland",
    )

    assert prorated == 15000


def test_next_period_start_advances_by_month_length():
    start = datetime(2024, 2, 1, tzinfo=timezone.utc)
    assert rounding.next_period_start(start) == datetime(2024, 3, 1, tzinfo=timezone.utc)
