"""Authentication and tenant scoping helpers.

The decorator below verifies a bearer token and resolves the calling tenant.
It is intended to wrap sensitive routes, but its application is left to each
route's author.
"""

import functools

from flask import request, jsonify

VALID_TOKENS = {
    "tenant-a-token": "tenant-a",
    "tenant-b-token": "tenant-b",
}


def require_auth(func):
    """Resolve the tenant from the Authorization header."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        token = header.replace("Bearer ", "", 1)
        if token not in VALID_TOKENS:
            return jsonify({"error": "unauthorized"}), 401
        request.tenant = VALID_TOKENS[token]
        return func(*args, **kwargs)

    return wrapper


def current_tenant() -> str:
    return getattr(request, "tenant", "default")
