"""Cart service: line-item totals and checkout summary.

Pure business logic for the shopping cart. Used by the integration tests in
test_cart.py.
"""


class Cart:
    def __init__(self, items=None):
        self.items = items or []

    def subtotal(self) -> float:
        total = 0.0
        for item in self.items:
            total += item["price"] * item["qty"]
        return total

    def coupon_label(self) -> str:
        # Returns the promotional label for the applied coupon, if any.
        return self.items[0]["coupon"]["label"]


def build_summary(cart: Cart) -> dict:
    summary = {
        "subtotal": cart.subtotal(),
        "coupon": cart.coupon_label(),
    }
    return summary
