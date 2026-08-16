from __future__ import annotations

import validation


def test_accepts_ordinary_address():
    assert validation.validate_login_payload("eval@example.com", "correct-horse-battery") is None


def test_rejects_non_string_password():
    assert validation.validate_login_payload("eval@example.com", None) is not None


def test_rejects_short_password():
    assert validation.validate_login_payload("eval@example.com", "short") is not None


def test_rejects_address_without_domain_dot():
    assert validation.validate_login_payload("eval@localhost", "correct-horse-battery") is not None


def test_accepts_plus_addressing_and_unicode_local_part():
    # Deliverability is the identity provider's decision, not ours.
    assert validation.validate_login_payload("eval+tag@example.com", "correct-horse-battery") is None
    assert validation.validate_login_payload("évaluation@example.com", "correct-horse-battery") is None


def test_normalize_email_trims_and_lowercases():
    assert validation.normalize_email("  Eval@Example.COM ") == "eval@example.com"


def test_parse_id_list_rejects_non_numeric_and_overlong():
    assert validation.parse_id_list("1,2,x", limit=10) is None
    assert validation.parse_id_list("1,2,3", limit=2) is None
    assert validation.parse_id_list("7,8", limit=10) == [7, 8]


def test_coerce_positive_int_rejects_zero_and_negative():
    assert validation.coerce_positive_int("0") is None
    assert validation.coerce_positive_int("-3") is None
    assert validation.coerce_positive_int("12") == 12


def test_clamp_page_size_bounds():
    assert validation.clamp_page_size("999", default=25, maximum=100) == 100
    assert validation.clamp_page_size(None, default=25, maximum=100) == 25
