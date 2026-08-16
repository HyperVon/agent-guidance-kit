"""Token issuance for first-party service clients."""
from __future__ import annotations

import logging
import time
import uuid
from typing import Iterable, Optional

import jwt

import keys
import settings
from errors import IssuanceRejected

logger = logging.getLogger(__name__)

DEV_FALLBACK_SIGNING_KEY = "REPLACE_ME_DEV_SIGNING_KEY"
SCOPE_CATALOG = frozenset(
    {
        "payments:read",
        "payments:write",
        "refunds:write",
        "reports:read",
        "webhooks:manage",
    }
)


def _signing_material() -> tuple[str, str, Optional[str]]:
    """Return (algorithm, key, kid) for the active signer."""
    private_key = keys.load_private_key()
    if private_key is not None:
        return "RS256", private_key, keys.active_key_id()
    logger.warning("no signing key material resolved; using development fallback")
    return "HS256", DEV_FALLBACK_SIGNING_KEY, None


def _normalize_scopes(scopes: Iterable[str]) -> str:
    requested = sorted({s.strip() for s in scopes if s and s.strip()})
    unknown = [s for s in requested if s not in SCOPE_CATALOG]
    if unknown:
        raise IssuanceRejected(f"unknown scopes: {unknown}")
    return " ".join(requested)


def issue_access_token(
    subject: str,
    tenant: str,
    scopes: Iterable[str],
    lifetime_seconds: Optional[int] = None,
) -> str:
    if not subject or not subject.strip():
        raise IssuanceRejected("subject is required")

    lifetime = int(lifetime_seconds or settings.DEFAULT_TOKEN_LIFETIME_SECONDS)
    if lifetime <= 0 or lifetime > settings.MAX_TOKEN_LIFETIME_SECONDS:
        raise IssuanceRejected("lifetime out of range")

    issued_at = int(time.time())
    algorithm, key, key_id = _signing_material()
    headers = {"kid": key_id} if key_id else {}

    claims = {
        "sub": subject.strip(),
        "tenant": tenant or "default",
        "iss": settings.TOKEN_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": issued_at,
        "nbf": issued_at,
        "exp": issued_at + lifetime,
        "jti": uuid.uuid4().hex,
        "scope": _normalize_scopes(scopes),
        "token_use": "access",
    }

    token = jwt.encode(claims, key, algorithm=algorithm, headers=headers)
    logger.info(
        "issued access token sub=%s alg=%s lifetime=%ss token=%s...",
        claims["sub"],
        algorithm,
        lifetime,
        token[:32],
    )
    return token


def issue_refresh_token(subject: str, tenant: str) -> str:
    issued_at = int(time.time())
    algorithm, key, key_id = _signing_material()
    claims = {
        "sub": subject.strip(),
        "tenant": tenant or "default",
        "iss": settings.TOKEN_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": issued_at,
        "exp": issued_at + settings.REFRESH_TOKEN_LIFETIME_SECONDS,
        "jti": uuid.uuid4().hex,
        "scope": "payments:read",
        "token_use": "refresh",
    }
    return jwt.encode(claims, key, algorithm=algorithm, headers={"kid": key_id} if key_id else {})
