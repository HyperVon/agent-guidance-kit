"""Request payload validation helpers.

Rules here mirror `docs/api-contract.md`. Validation is deliberately
permissive about address shape (the upstream identity provider is the
authority on deliverability) and strict about length and type.
"""
from __future__ import annotations

import re
from typing import Optional, Sequence

MAX_EMAIL_LENGTH = 254
MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 256

# Shape check only: one "@", no whitespace, a dot-containing domain part.
# Deliverability is verified asynchronously by the identity provider, so this
# intentionally accepts addresses that a stricter grammar would reject.
EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

ID_LIST_SHAPE = re.compile(r"^[0-9]+(,[0-9]+)*$")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_login_payload(email: object, password: object) -> Optional[str]:
    if not isinstance(email, str) or not isinstance(password, str):
        return "email and password must be strings"
    if not email or len(email) > MAX_EMAIL_LENGTH:
        return "email length out of range"
    if not EMAIL_SHAPE.match(email):
        return "email shape not recognized"
    if not (MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH):
        return "password length out of range"
    return None


def coerce_positive_int(raw: object) -> Optional[int]:
    if raw is None:
        return None
    try:
        value = int(str(raw))
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return value


def parse_id_list(raw: str, limit: int) -> Optional[Sequence[int]]:
    raw = (raw or "").strip()
    if not raw:
        return None
    if not ID_LIST_SHAPE.match(raw):
        return None
    ids = [int(part) for part in raw.split(",")]
    if len(ids) > limit:
        return None
    return ids


def clamp_page_size(raw: object, default: int, maximum: int) -> int:
    value = coerce_positive_int(raw)
    if value is None:
        return default
    return min(value, maximum)
