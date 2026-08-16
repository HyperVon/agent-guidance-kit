"""Cache key construction and versioning."""
from __future__ import annotations

from store import repository

# Bumped by hand when the serialized payload shape changes. See ADR 0007.
SCHEMA_VERSION = "v7"


def build(namespace: str, entity_id: str) -> str:
    content_version = repository.content_version(namespace)
    return f"cat:{SCHEMA_VERSION}:{namespace}:{content_version}:{entity_id}"


def namespace_prefix(namespace: str) -> str:
    content_version = repository.content_version(namespace)
    return f"cat:{SCHEMA_VERSION}:{namespace}:{content_version}:"
