"""Public read endpoints for the catalog."""
from __future__ import annotations

import json
import logging

from flask import Blueprint, jsonify, request

from cache.store import CacheStore
from store import repository

logger = logging.getLogger(__name__)

api = Blueprint("catalog", __name__)
_store: CacheStore | None = None


def attach(store: CacheStore) -> None:
    global _store
    _store = store


@api.get("/v1/layers/<layer_id>")
def get_layer(layer_id: str):
    assert _store is not None, "cache store not attached"
    try:
        payload = _store.get_or_load(
            "layer", layer_id, lambda: repository.load_layer(layer_id)
        )
    except KeyError:
        return jsonify({"error": "not_found"}), 404
    body = json.loads(payload)
    return jsonify(body), 200


@api.get("/v1/layers")
def list_layers():
    limit = min(int(request.args.get("limit", "50")), 200)
    ids = repository.top_entity_ids("layer", limit)
    return jsonify({"layer_ids": ids}), 200


@api.get("/v1/cache/status")
def cache_status():
    assert _store is not None, "cache store not attached"
    return jsonify({"degraded_namespaces": sorted(_store.degraded)}), 200
