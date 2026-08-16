"""Currency rounding and proration helpers.

All amounts are integer minor units unless a name says otherwise.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

MINOR_UNITS = {"USD": 2, "EUR": 2, "JPY": 0, "BHD": 3}


def minor_units(currency: str) -> int:
    return MINOR_UNITS.get(currency.upper(), 2)


def to_minor(amount: Decimal, currency: str) -> int:
    scale = Decimal(10) ** minor_units(currency)
    return int((amount * scale).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def split_evenly(total_minor: int, parts: int) -> list[int]:
    """Split a total into `parts` amounts that sum exactly to the total."""
    if parts <= 0:
        raise ValueError("parts must be positive")
    base, remainder = divmod(total_minor, parts)
    return [base + (1 if i < remainder else 0) for i in range(parts)]


def days_in_month(anchor: date) -> int:
    return calendar.monthrange(anchor.year, anchor.month)[1]


def proration_factor(
    changed_at: datetime, period_start: datetime, period_end: datetime
) -> Decimal:
    if not (period_start <= changed_at <= period_end):
        raise ValueError("changed_at outside the billing period")
    total = Decimal((period_end - period_start).total_seconds())
    remaining = Decimal((period_end - changed_at).total_seconds())
    if total == 0:
        return Decimal(0)
    return remaining / total


def local_day_boundary(moment: datetime, tenant_timezone: str) -> datetime:
    """Start of the local day containing `moment`, returned in UTC."""
    tz = ZoneInfo(tenant_timezone)
    local = moment.astimezone(tz)
    start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_local.astimezone(timezone.utc)


def prorate_upgrade(
    amount_minor: int,
    currency: str,
    changed_at: datetime,
    period_start: datetime,
    period_end: datetime,
    tenant_timezone: str = "UTC",
) -> int:
    boundary = local_day_boundary(changed_at, tenant_timezone)
    factor = proration_factor(boundary, period_start, period_end)
    scaled = Decimal(amount_minor) * factor
    return int(scaled.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def next_period_start(period_start: datetime) -> datetime:
    days = days_in_month(period_start.date())
    return period_start + timedelta(days=days)
