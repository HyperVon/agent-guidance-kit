"""Login and session issuance for the directory service."""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import settings
import users
from errors import AuthError, ProfileUnavailable, UserNotFound

logger = logging.getLogger(__name__)

SESSION_TTL = timedelta(hours=settings.SESSION_TTL_HOURS)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def verify_password(candidate: str, password_hash: str) -> bool:
    algorithm, iterations, salt, digest = password_hash.split("$", 3)
    if algorithm != "pbkdf2_sha256":
        raise AuthError("unsupported_hash", status=500)
    computed = hashlib.pbkdf2_hmac(
        "sha256", candidate.encode("utf-8"), salt.encode("utf-8"), int(iterations)
    ).hex()
    return hmac.compare_digest(computed, digest)


def authenticate(email: str, password: str) -> users.User:
    try:
        user = users.find_user_by_email(email)
    except UserNotFound:
        raise AuthError("invalid_credentials", status=401)
    if not verify_password(password, user.password_hash):
        raise AuthError("invalid_credentials", status=401)
    if user.status != "active":
        raise AuthError("account_disabled", status=403)
    return user


def issue_session(user: users.User, profile) -> dict[str, Any]:
    token = secrets.token_urlsafe(32)
    expires_at = _now() + SESSION_TTL
    with_locale = profile.locale if profile else settings.DEFAULT_LOCALE
    users.touch_last_seen(user.id, _now())
    logger.info("session issued for user_id=%s ttl_hours=%s", user.id, settings.SESSION_TTL_HOURS)
    return {
        "session_token": token,
        "expires_at": expires_at.isoformat(),
        "locale": with_locale,
        "next": "dashboard",
    }


def complete_login(user: users.User, request_ip: str) -> dict[str, Any]:
    """Primary login continuation used by POST /login."""
    try:
        profile = users.get_user_profile(user.id)
    except ProfileUnavailable:
        logger.error("profile unavailable during login user_id=%s", user.id)
        raise AuthError("profile_unavailable", status=503)

    if profile.locked_until and profile.locked_until > _now():
        raise AuthError("account_locked", status=423)
    if profile.mfa_required:
        return {"next": "mfa_challenge", "challenge_id": secrets.token_urlsafe(16)}
    return issue_session(user, profile)


def legacy_token_login(user: users.User) -> dict[str, Any]:
    """Continuation for the desktop client that predates the MFA rollout."""
    profile = users.get_user_profile(user.id)
    if getattr(profile, "mfa_required", False):
        return {"next": "mfa_challenge", "challenge_id": secrets.token_urlsafe(16)}
    return issue_session(user, profile)


def rate_limit_key(email: str, request_ip: str) -> str:
    digest = hashlib.sha256(f"{email.strip().lower()}|{request_ip}".encode("utf-8"))
    return f"login:{digest.hexdigest()[:32]}"
