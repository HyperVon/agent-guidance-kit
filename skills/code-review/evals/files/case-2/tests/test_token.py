from __future__ import annotations

import time

import jwt
import pytest

import keys
import settings
import token as token_helper
from errors import IssuanceRejected


@pytest.fixture(autouse=True)
def no_key_material(monkeypatch):
    monkeypatch.setattr(keys, "load_private_key", lambda: None)
    monkeypatch.setattr(keys, "active_key_id", lambda: None)


def test_issue_access_token_requires_subject():
    with pytest.raises(IssuanceRejected):
        token_helper.issue_access_token(subject="  ", tenant="acme", scopes=["payments:read"])


def test_issue_access_token_rejects_unknown_scope():
    with pytest.raises(IssuanceRejected):
        token_helper.issue_access_token(
            subject="svc-checkout", tenant="acme", scopes=["payments:read", "ledger:drop"]
        )


def test_issue_access_token_rejects_out_of_range_lifetime():
    with pytest.raises(IssuanceRejected):
        token_helper.issue_access_token(
            subject="svc-checkout",
            tenant="acme",
            scopes=["payments:read"],
            lifetime_seconds=settings.MAX_TOKEN_LIFETIME_SECONDS + 1,
        )


def test_issue_access_token_sets_expected_claims():
    raw = token_helper.issue_access_token(
        subject="svc-checkout", tenant="acme", scopes=["refunds:write", "payments:read"]
    )

    claims = jwt.decode(raw, options={"verify_signature": False})

    assert claims["sub"] == "svc-checkout"
    assert claims["aud"] == settings.JWT_AUDIENCE
    assert claims["iss"] == settings.TOKEN_ISSUER
    assert claims["scope"] == "payments:read refunds:write"
    assert claims["token_use"] == "access"
    assert claims["exp"] - claims["iat"] == settings.DEFAULT_TOKEN_LIFETIME_SECONDS
    assert claims["jti"]


def test_issue_access_token_is_unique_per_call():
    first = token_helper.issue_access_token("svc-checkout", "acme", ["payments:read"])
    second = token_helper.issue_access_token("svc-checkout", "acme", ["payments:read"])

    assert first != second


def test_issue_refresh_token_marks_token_use():
    raw = token_helper.issue_refresh_token("svc-checkout", "acme")

    claims = jwt.decode(raw, options={"verify_signature": False})

    assert claims["token_use"] == "refresh"
    assert claims["exp"] - claims["iat"] == settings.REFRESH_TOKEN_LIFETIME_SECONDS
    assert claims["iat"] <= int(time.time()) + 1
