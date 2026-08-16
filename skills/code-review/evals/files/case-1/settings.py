"""Environment-driven configuration. No values are committed here."""
from __future__ import annotations

import os

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
DEFAULT_LOCALE = os.environ.get("DEFAULT_LOCALE", "en-US")

SESSION_TTL_HOURS = int(os.environ.get("SESSION_TTL_HOURS", "12"))
EXPORT_MAX_IDS = int(os.environ.get("EXPORT_MAX_IDS", "500"))

DB_POOL_MIN = int(os.environ.get("DB_POOL_MIN", "1"))
DB_POOL_MAX = int(os.environ.get("DB_POOL_MAX", "8"))
DB_CONNECT_TIMEOUT_SECONDS = float(os.environ.get("DB_CONNECT_TIMEOUT_SECONDS", "5"))

IDENTITY_PROVIDER_URL = os.environ.get(
    "IDENTITY_PROVIDER_URL", "https://identity.example.com"
)


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return url
