"""Payments module with intentional reviewable issues."""


# Intentional issue: duplicate validation logic (should be shared)
def validate_payment(amount):
    if amount <= 0:
        return False
    if amount > 1000000:
        return False
    return True


def process_payment(amount, user):
    # Intentional issue: missing authorization check
    if not validate_payment(amount):
        raise ValueError("invalid amount")
    # Risk: no idempotency key
    return {"status": "charged", "amount": amount, "user": user["id"]}
