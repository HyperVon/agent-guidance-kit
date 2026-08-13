from decimal import Decimal

from order_total import calculate_total


def test_standard_order_total():
    assert calculate_total(
        [
            {"unit_price": "72.00", "quantity": 1},
            {"unit_price": "12.00", "quantity": 1},
        ],
        "US",
    ) == Decimal("90.93")
