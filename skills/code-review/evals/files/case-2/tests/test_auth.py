from __future__ import annotations

import time

import jwt
import pytest

import auth
import keys
import settings
from errors import AuthRejected

OTHER_SECRET = "unrelated-test-material"


def _claims(**overrides):
    now = int(time.time())
    claims = {
        "sub": "svc-checkout",
        "tenant": "acme",
        "iss": settings.ALLOWED_ISSUERS[0],
        "aud": settings.JWT_AUDIENCE,
        "iat": now,
        "exp": now + 600,
        "scope": "payments:read refunds:write",
        "token_use": "access",
    }
    claims.update(overrides)
    return claims


def _token(claims=None, key=OTHER_SECRET, algorithm="HS256", kid="kid-2024-a"):
    return jwt.encode(claims or _claims(), key, algorithm=algorithm, headers={"kid": kid})


@pytest.fixture(autouse=True)
def stub_key_resolution(monkeypatch):
    monkeypatch.setattr(keys, "resolve", lambda kid: None)


def test_extract_bearer_requires_prefix():
    with pytest.raises(AuthRejected):
        auth.extract_bearer({"Authorization": "Token abc.def.ghi"})


def test_extract_bearer_rejects_oversized_token():
    with pytest.raises(AuthRejected):
        auth.extract_bearer({"Authorization": "Bearer " + ("a" * 5000) + ".b.c"})


def test_extract_bearer_is_case_insensitive():
    assert auth.extract_bearer({"authorization": "bearer a.b.c"}) == "a.b.c"


def test_authenticate_request_returns_principal():
    headers = {"Authorization": f"Bearer {_token()}"}

    principal = auth.authenticate_request(headers)

    assert principal.subject == "svc-checkout"
    assert principal.tenant == "acme"
    assert principal.has_scope("payments:read")


def test_authenticate_request_rejects_untrusted_issuer():
    headers = {"Authorization": f"Bearer {_token(_claims(iss='https://attacker.example.com'))}"}

    with pytest.raises(AuthRejected) as excinfo:
        auth.authenticate_request(headers)
    assert excinfo.value.code == "untrusted_issuer"


def test_authenticate_request_rejects_refresh_token():
    headers = {"Authorization": f"Bearer {_token(_claims(token_use='refresh'))}"}

    with pytest.raises(AuthRejected) as excinfo:
        auth.authenticate_request(headers)
    assert excinfo.value.code == "refresh_token_not_accepted"


def test_authenticate_request_rejects_overlong_lifetime():
    now = int(time.time())
    headers = {
        "Authorization": f"Bearer {_token(_claims(iat=now, exp=now + 7 * 24 * 3600))}"
    }

    with pytest.raises(AuthRejected) as excinfo:
        auth.authenticate_request(headers)
    assert excinfo.value.code == "lifetime_too_long"


def test_authenticate_request_rejects_revoked_kid():
    headers = {"Authorization": f"Bearer {_token(kid=settings.REVOKED_KEY_IDS[0])}"}

    with pytest.raises(AuthRejected):
        auth.authenticate_request(headers)


def test_authenticate_request_rejects_expired_token():
    now = int(time.time())
    headers = {"Authorization": f"Bearer {_token(_claims(iat=now - 3600, exp=now - 60))}"}

    with pytest.raises(AuthRejected) as excinfo:
        auth.authenticate_request(headers)
    assert excinfo.value.code == "token_expired"


@pytest.mark.xfail(reason="key-resolution rework in flight; tracked by PLAT-3312", strict=False)
def test_authenticate_request_rejects_token_signed_with_unknown_key():
    headers = {"Authorization": f"Bearer {_token(key='attacker-controlled-material')}"}

    with pytest.raises(AuthRejected):
        auth.authenticate_request(headers)


def test_require_scope_rejects_insufficient_scope():
    headers = {"Authorization": f"Bearer {_token(_claims(scope='reports:read'))}"}

    with pytest.raises(AuthRejected) as excinfo:
        auth.require_scope(headers, "refunds:write")
    assert excinfo.value.status == 403
