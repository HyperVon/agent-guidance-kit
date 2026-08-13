from decimal import Decimal, ROUND_HALF_UP


def calculate_total(items, country, coupon=None):
    subtotal = sum(
        Decimal(str(item["unit_price"])) * int(item["quantity"]) for item in items
    )
    if coupon == "WELCOME10":
        subtotal -= Decimal("10.00")

    shipping = Decimal("0.00") if subtotal >= Decimal("75.00") else Decimal("8.00")
    tax_rate = Decimal("0.0825") if country == "US" else Decimal("0.00")
    tax = (subtotal * tax_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return (subtotal + shipping + tax).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
