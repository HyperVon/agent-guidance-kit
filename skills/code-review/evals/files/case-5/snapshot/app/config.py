"""Environment configuration. No secret values are committed."""
from __future__ import annotations

import os

SERVICE_NAME = "reporting-api"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

DEFAULT_PAGE_SIZE = int(os.environ.get("DEFAULT_PAGE_SIZE", "50"))
MAX_EXPORT_LIMIT = int(os.environ.get("MAX_EXPORT_LIMIT", "500"))

EXPORT_API_KEY = os.environ.get("EXPORT_API_KEY", "REPLACE_ME_API_KEY")


def api_key() -> str:
    """Return the reporting API key, or fail closed when it is not configured."""
    value = os.environ.get("REPORTING_API_KEY")
    if not value:
        raise RuntimeError("REPORTING_API_KEY is not configured")
    return value
