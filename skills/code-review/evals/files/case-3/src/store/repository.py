"""Postgres-backed source of truth for the catalog."""
from __future__ import annotations

import json
from typing import Any

_LAYERS: dict[str, dict[str, Any]] = {
    "layer-basemap": {"id": "layer-basemap", "srid": 3857, "tiles": "raster", "min_zoom": 0},
    "layer-transit": {"id": "layer-transit", "srid": 3857, "tiles": "vector", "min_zoom": 6},
    "layer-parcels": {"id": "layer-parcels", "srid": 4326, "tiles": "vector", "min_zoom": 12},
}

_CONTENT_VERSIONS: dict[str, int] = {"layer": 41, "style": 12, "manifest": 8}


def load_layer(entity_id: str) -> bytes:
    record = _LAYERS.get(entity_id)
    if record is None:
        raise KeyError(entity_id)
    return json.dumps(record, separators=(",", ":")).encode("utf-8")


def content_version(namespace: str) -> int:
    return _CONTENT_VERSIONS.get(namespace, 1)


def bump_content_version(namespace: str) -> int:
    _CONTENT_VERSIONS[namespace] = content_version(namespace) + 1
    return _CONTENT_VERSIONS[namespace]


def top_entity_ids(namespace: str, limit: int) -> list[str]:
    if namespace != "layer":
        return []
    return list(_LAYERS)[:limit]
