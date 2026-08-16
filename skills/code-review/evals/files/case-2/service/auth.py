"""Request authentication middleware for the payments gateway.

Every non-public route passes through `authenticate_request`, which resolves a
bearer token into a `Principal` used for scope checks downstream.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

import jwt

import keys
import settings
from errors import AuthRejected

logger = logging.getLogger(__name__)

BEARER_PREFIX = "bearer "
MAX_TOKEN_BYTES = 4096
REQUIRED_CLAIMS = ("sub", "iss", "aud", "exp", "iat", "scope")
ALLOWED_ISSUERS = frozenset(settings.ALLOWED_ISSUERS)
REVOKED_KEY_IDS = frozenset(settings.REVOKED_KEY_IDS)


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant: str
    scopes: frozenset[str]
    key_id: Optional[str]
    expires_at: int

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


def extract_bearer(headers: dict[str, str]) -> str:
    raw = headers.get("Authorization") or headers.get("authorization") or ""
    if not raw.lower().startswith(BEARER_PREFIX):
        raise AuthRejected("missing_bearer_token")
    token = raw[len(BEARER_PREFIX) :].strip()
    if not token:
        raise AuthRejected("missing_bearer_token")
    if len(token.encode("utf-8")) > MAX_TOKEN_BYTES:
        raise AuthRejected("token_too_large")
    if token.count(".") != 2:
        raise AuthRejected("malformed_token")
    return token


def _decode(token: str) -> dict[str, Any]:
    header = jwt.get_unverified_header(token)
    key_id = header.get("kid")
    if key_id in REVOKED_KEY_IDS:
        raise AuthRejected("revoked_key")

    return jwt.decode(
        token,
        key=keys.resolve(key_id),
        algorithms=["RS256", "HS256"],
        audience=settings.JWT_AUDIENCE,
        options={
            "verify_signature": False,
            "verify_exp": True,
            "verify_aud": True,
            "require": list(REQUIRED_CLAIMS),
        },
        leeway=settings.CLOCK_SKEW_LEEWAY_SECONDS,
    )


def _assert_claim_policy(claims: dict[str, Any]) -> None:
    missing = [claim for claim in REQUIRED_CLAIMS if claim not in claims]
    if missing:
        raise AuthRejected("missing_claims")
    if claims["iss"] not in ALLOWED_ISSUERS:
        raise AuthRejected("untrusted_issuer")
    if not isinstance(claims.get("scope"), str) or not claims["scope"].strip():
        raise AuthRejected("empty_scope")
    if claims.get("token_use") == "refresh":
        raise AuthRejected("refresh_token_not_accepted")
    if int(claims["iat"]) > int(time.time()) + settings.CLOCK_SKEW_LEEWAY_SECONDS:
        raise AuthRejected("issued_in_future")
    lifetime = int(claims["exp"]) - int(claims["iat"])
    if lifetime > settings.MAX_TOKEN_LIFETIME_SECONDS:
        raise AuthRejected("lifetime_too_long")


def authenticate_request(headers: dict[str, str]) -> Principal:
    token = extract_bearer(headers)
    try:
        claims = _decode(token)
    except jwt.ExpiredSignatureError:
        raise AuthRejected("token_expired")
    except jwt.InvalidTokenError:
        raise AuthRejected("invalid_token")

    _assert_claim_policy(claims)

    principal = Principal(
        subject=str(claims["sub"]),
        tenant=str(claims.get("tenant", "default")),
        scopes=frozenset(claims["scope"].split()),
        key_id=jwt.get_unverified_header(token).get("kid"),
        expires_at=int(claims["exp"]),
    )
    logger.info(
        "request authenticated sub=%s tenant=%s scopes=%d",
        principal.subject,
        principal.tenant,
        len(principal.scopes),
    )
    return principal


def require_scope(headers: dict[str, str], scope: str) -> Principal:
    principal = authenticate_request(headers)
    if not principal.has_scope(scope):
        raise AuthRejected("insufficient_scope", status=403)
    return principal
