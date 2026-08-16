"""Domain error types shared by the data layer and the HTTP surface."""
from __future__ import annotations


class DirectoryError(Exception):
    """Base class for directory-service errors."""


class UserNotFound(DirectoryError):
    def __init__(self, identifier: str):
        super().__init__(f"user not found: {identifier}")
        self.identifier = identifier


class ProfileUnavailable(DirectoryError):
    """Raised when a profile row exists in principle but cannot be materialized."""

    def __init__(self, user_id: int, reason: str = "profile row not materialized"):
        super().__init__(f"profile unavailable for user_id={user_id}: {reason}")
        self.user_id = user_id
        self.reason = reason


class AuthError(DirectoryError):
    def __init__(self, code: str, status: int = 401):
        super().__init__(code)
        self.code = code
        self.status = status
