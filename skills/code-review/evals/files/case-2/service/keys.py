"""Signing-key resolution and JWKS caching."""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Optional

import requests

import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_cache: dict[str, Any] = {"fetched_at": 0.0, "keys": {}}


def _fetch_jwks() -> dict[str, Any]:
    response = requests.get(
        settings.JWKS_URL,
        timeout=settings.JWKS_TIMEOUT_SECONDS,
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    document = response.json()
    if not isinstance(document.get("keys"), list):
        raise ValueError("JWKS document has no key array")
    return {entry["kid"]: entry for entry in document["keys"] if entry.get("kid")}


def _cached_keys() -> dict[str, Any]:
    with _lock:
        age = time.monotonic() - _cache["fetched_at"]
        if _cache["keys"] and age < settings.JWKS_TTL_SECONDS:
            return _cache["keys"]
    fresh = _fetch_jwks()
    with _lock:
        _cache["keys"] = fresh
        _cache["fetched_at"] = time.monotonic()
        return fresh


def resolve(key_id: Optional[str]):
    """Return the verification key for ``key_id``."""
    entries = _cached_keys()
    if key_id is None:
        if len(entries) == 1:
            return _to_public_key(next(iter(entries.values())))
        raise ValueError("token has no kid and the key set is ambiguous")
    entry = entries.get(key_id)
    if entry is None:
        raise ValueError(f"unknown kid: {key_id}")
    return _to_public_key(entry)


def _to_public_key(entry: dict[str, Any]):
    from jwt.algorithms import RSAAlgorithm

    return RSAAlgorithm.from_jwk(json.dumps(entry))


def active_key_id() -> Optional[str]:
    return os.environ.get("JWT_ACTIVE_KID")


def load_private_key() -> Optional[str]:
    """Read the PEM signing key from the path in the environment, if present."""
    path = os.environ.get("JWT_PRIVATE_KEY_PATH")
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        logger.warning("could not read signing key material: %s", exc.strerror)
        return None


def invalidate_cache() -> None:
    with _lock:
        _cache["keys"] = {}
        _cache["fetched_at"] = 0.0
