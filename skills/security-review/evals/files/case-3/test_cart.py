"""Integration test for the cart service.

Reproduces the failing scenario: a cart with no items raises a
NullPointerException when build_summary tries to read a coupon label.
"""

import unittest

from cart import Cart, build_summary


class CartSummaryTest(unittest.TestCase):
    def test_empty_cart_summary(self):
        cart = Cart(items=[])
        summary = build_summary(cart)
        self.assertEqual(summary["subtotal"], 0.0)


if __name__ == "__main__":
    unittest.main()
