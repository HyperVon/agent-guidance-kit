"""API key checks for the reporting endpoints."""
from __future__ import annotations

import hmac
from typing import Optional

from app import config
from app.router import Request, Response

API_KEY_HEADER = "X-Api-Key"


def require_api_key(request: Request) -> Optional[Response]:
    """Return an error response when the request is not authorized."""
    provided = request.headers.get(API_KEY_HEADER, "")
    if not provided:
        return Response.error(401, "unauthorized")
    try:
        expected = config.api_key()
    except RuntimeError:
        return Response.error(503, "api_key_not_configured")
    if not hmac.compare_digest(provided, expected):
        return Response.error(401, "unauthorized")
    return None


def require_export_key(request: Request) -> Optional[Response]:
    """Return an error response when the export request is not authorized."""
    provided = request.headers.get(API_KEY_HEADER, "")
    if not provided:
        return Response.error(401, "unauthorized")
    if not hmac.compare_digest(provided, config.EXPORT_API_KEY):
        return Response.error(401, "unauthorized")
    return None
