"""Two-tier cache: per-pod LRU (L1) in front of Redis (L2)."""
from __future__ import annotations

import logging
import time
from collections import OrderedDict
from threading import RLock
from typing import Callable, Optional

from cache import keys
from config import cache_config

logger = logging.getLogger(__name__)


class _LRU:
    def __init__(self, max_entries: int):
        self._max = max_entries
        self._data: "OrderedDict[str, tuple[float, bytes]]" = OrderedDict()
        self._lock = RLock()

    def get(self, key: str, ttl_seconds: float) -> Optional[bytes]:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            stored_at, value = item
            if time.monotonic() - stored_at > ttl_seconds:
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key)
            return value

    def put(self, key: str, value: bytes) -> None:
        with self._lock:
            self._data[key] = (time.monotonic(), value)
            self._data.move_to_end(key)
            while len(self._data) > self._max:
                self._data.popitem(last=False)

    def evict(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)


class CacheStore:
    def __init__(self, redis_client, l1: Optional[_LRU] = None):
        self._redis = redis_client
        cfg = cache_config()
        self._l1 = l1 or _LRU(cfg["l1_max_entries"])
        self._degraded_namespaces: set[str] = set()

    def get_or_load(
        self, namespace: str, entity_id: str, loader: Callable[[], bytes]
    ) -> bytes:
        cfg = cache_config()["namespaces"][namespace]
        key = keys.build(namespace, entity_id)

        hit = self._l1.get(key, cfg["l1_ttl_seconds"])
        if hit is not None:
            return hit

        value = self._l2_get(namespace, key)
        if value is not None:
            self._l1.put(key, value)
            return value

        value = loader()
        self._l2_put(namespace, key, value, cfg["l2_ttl_seconds"])
        self._l1.put(key, value)
        return value

    def _l2_get(self, namespace: str, key: str) -> Optional[bytes]:
        try:
            return self._redis.get(key)
        except Exception:
            self._mark_degraded(namespace)
            return None

    def _l2_put(self, namespace: str, key: str, value: bytes, ttl_seconds: int) -> None:
        try:
            self._redis.set(key, value, ex=ttl_seconds)
        except Exception:
            self._mark_degraded(namespace)

    def evict(self, namespace: str, entity_id: str) -> None:
        key = keys.build(namespace, entity_id)
        self._l1.evict(key)
        try:
            self._redis.delete(key)
        except Exception:
            self._mark_degraded(namespace)

    def _mark_degraded(self, namespace: str) -> None:
        if namespace not in self._degraded_namespaces:
            logger.warning("cache namespace degraded, falling back to source: %s", namespace)
            self._degraded_namespaces.add(namespace)

    @property
    def degraded(self) -> frozenset[str]:
        return frozenset(self._degraded_namespaces)
