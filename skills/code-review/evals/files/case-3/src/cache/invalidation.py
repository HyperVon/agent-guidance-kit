"""Invalidation fan-out driven by publish events."""
from __future__ import annotations

import json
import logging

from cache.store import CacheStore

logger = logging.getLogger(__name__)

INVALIDATION_CHANNEL = "catalog.invalidate"


def on_publish_event(store: CacheStore, redis_client, event: dict) -> None:
    namespace = event["namespace"]
    entity_id = event["entity_id"]

    store.evict(namespace, entity_id)
    try:
        redis_client.publish(
            INVALIDATION_CHANNEL,
            json.dumps({"namespace": namespace, "entity_id": entity_id}),
        )
    except Exception:
        logger.warning("invalidation broadcast failed namespace=%s", namespace)


def on_broadcast_message(store: CacheStore, raw: bytes) -> None:
    payload = json.loads(raw)
    store.evict(payload["namespace"], payload["entity_id"])
