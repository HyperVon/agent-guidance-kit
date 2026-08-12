"""Payments module with intentional reviewable issues."""


def validate_payment(amount):
    if amount <= 0:
        return False
    if amount > 1000000:
        return False
    return True


def process_payment(amount, user):
    if not validate_payment(amount):
        raise ValueError("invalid amount")
    return {"status": "charged", "amount": amount, "user": user["id"]}
