"""Error types for the gateway."""
from __future__ import annotations


class GatewayError(Exception):
    """Base class."""


class AuthRejected(GatewayError):
    """Raised when a request cannot be authenticated or is not permitted.

    The `code` is safe to return to the caller; it never includes token
    material or claim values.
    """

    def __init__(self, code: str, status: int = 401):
        super().__init__(code)
        self.code = code
        self.status = status


class IssuanceRejected(GatewayError):
    """Raised when a token issuance request violates policy."""
