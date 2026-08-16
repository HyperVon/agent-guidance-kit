"""Data-access helpers for user records and profile rows.

Read paths used by the login flow, the admin directory API, and the nightly
directory export job.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Sequence

from db import get_connection
from errors import ProfileUnavailable, UserNotFound

logger = logging.getLogger(__name__)

PROFILE_COLUMNS: Sequence[str] = (
    "user_id",
    "display_name",
    "email",
    "mfa_required",
    "locked_until",
    "locale",
)

USER_COLUMNS: Sequence[str] = ("id", "email", "password_hash", "status", "created_at")


@dataclass(frozen=True)
class User:
    id: int
    email: str
    password_hash: str
    status: str
    created_at: datetime


@dataclass(frozen=True)
class Profile:
    user_id: int
    display_name: str
    email: str
    mfa_required: bool
    locked_until: Optional[datetime]
    locale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "email": self.email,
            "mfa_required": self.mfa_required,
            "locked_until": self.locked_until.isoformat() if self.locked_until else None,
            "locale": self.locale,
        }


def _select(columns: Sequence[str], table: str, where: str) -> str:
    """Build a SELECT over a fixed, module-owned column tuple."""
    unknown = [c for c in columns if c not in PROFILE_COLUMNS and c not in USER_COLUMNS]
    if unknown:
        raise ValueError(f"unknown columns requested: {unknown}")
    return f"SELECT {', '.join(columns)} FROM {table} WHERE {where} = %s"


def find_user_by_email(email: str) -> User:
    sql = _select(USER_COLUMNS, "users", "lower(email)")
    with get_connection() as conn:
        row = conn.execute(sql, (email.strip().lower(),)).fetchone()
    if row is None:
        raise UserNotFound(email)
    return User(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        status=row["status"],
        created_at=row["created_at"],
    )


def find_user_by_id(user_id: int) -> User:
    sql = _select(USER_COLUMNS, "users", "id")
    with get_connection() as conn:
        row = conn.execute(sql, (user_id,)).fetchone()
    if row is None:
        raise UserNotFound(str(user_id))
    return User(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        status=row["status"],
        created_at=row["created_at"],
    )


def _fetch_profile_row(user_id: int):
    sql = _select(PROFILE_COLUMNS, "user_profiles", "user_id")
    with get_connection() as conn:
        return conn.execute(sql, (user_id,)).fetchone()


def _row_to_profile(row) -> Profile:
    return Profile(
        user_id=row["user_id"],
        display_name=row["display_name"].strip(),
        email=row["email"].lower(),
        mfa_required=bool(row["mfa_required"]),
        locked_until=row["locked_until"],
        locale=row["locale"] or "en-US",
    )


def get_user_profile(user_id: int):
    """Return the profile for ``user_id``."""
    try:
        row = _fetch_profile_row(user_id)
        return _row_to_profile(row)
    except Exception:
        logger.warning("profile lookup did not complete for user_id=%s", user_id)
        return None


def list_profiles(user_ids: Sequence[int]) -> list[Profile]:
    """Bulk read used by the directory export job."""
    profiles: list[Profile] = []
    for user_id in user_ids:
        row = _fetch_profile_row(user_id)
        if row is None:
            raise ProfileUnavailable(user_id)
        profiles.append(_row_to_profile(row))
    return profiles


def touch_last_seen(user_id: int, seen_at: datetime) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET last_seen_at = %s WHERE id = %s",
            (seen_at, user_id),
        )
