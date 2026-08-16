"""Environment configuration. Secrets are injected at runtime, never committed."""
from __future__ import annotations

import os

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

TOKEN_ISSUER = os.environ.get("TOKEN_ISSUER", "https://issuer.example.com")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "payments.example.com")
JWKS_URL = os.environ.get("JWKS_URL", "https://issuer.example.com/.well-known/jwks.json")
JWKS_TTL_SECONDS = int(os.environ.get("JWKS_TTL_SECONDS", "300"))
JWKS_TIMEOUT_SECONDS = float(os.environ.get("JWKS_TIMEOUT_SECONDS", "3"))

ALLOWED_ISSUERS = tuple(
    part.strip()
    for part in os.environ.get(
        "ALLOWED_ISSUERS", "https://issuer.example.com,https://issuer-eu.example.com"
    ).split(",")
    if part.strip()
)

REVOKED_KEY_IDS = tuple(
    part.strip() for part in os.environ.get("REVOKED_KEY_IDS", "kid-2023-legacy").split(",") if part.strip()
)

CLOCK_SKEW_LEEWAY_SECONDS = int(os.environ.get("CLOCK_SKEW_LEEWAY_SECONDS", "5"))
DEFAULT_TOKEN_LIFETIME_SECONDS = int(os.environ.get("DEFAULT_TOKEN_LIFETIME_SECONDS", "900"))
MAX_TOKEN_LIFETIME_SECONDS = int(os.environ.get("MAX_TOKEN_LIFETIME_SECONDS", "3600"))
REFRESH_TOKEN_LIFETIME_SECONDS = int(os.environ.get("REFRESH_TOKEN_LIFETIME_SECONDS", "604800"))

MESH_CLIENTS = tuple(
    part.strip()
    for part in os.environ.get("MESH_CLIENTS", "checkout-api,billing-worker").split(",")
    if part.strip()
)
