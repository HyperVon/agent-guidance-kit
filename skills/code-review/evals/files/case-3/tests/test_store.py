from __future__ import annotations

import time

import pytest

from cache import keys
from cache.store import CacheStore, _LRU


class FakeRedis:
    def __init__(self, fail=False):
        self.data: dict[str, bytes] = {}
        self.fail = fail
        self.published: list[tuple[str, str]] = []

    def get(self, key):
        if self.fail:
            raise ConnectionError("redis unavailable")
        return self.data.get(key)

    def set(self, key, value, ex=None):
        if self.fail:
            raise ConnectionError("redis unavailable")
        self.data[key] = value

    def delete(self, key):
        if self.fail:
            raise ConnectionError("redis unavailable")
        self.data.pop(key, None)

    def publish(self, channel, message):
        self.published.append((channel, message))


@pytest.fixture
def store():
    return CacheStore(FakeRedis(), l1=_LRU(max_entries=4))


def test_loader_runs_once_for_repeat_reads(store):
    calls = []

    def loader():
        calls.append(1)
        return b'{"id":"layer-basemap"}'

    store.get_or_load("layer", "layer-basemap", loader)
    store.get_or_load("layer", "layer-basemap", loader)

    assert len(calls) == 1


def test_eviction_forces_reload(store):
    calls = []

    def loader():
        calls.append(1)
        return b'{"id":"layer-transit"}'

    store.get_or_load("layer", "layer-transit", loader)
    store.evict("layer", "layer-transit")
    store.get_or_load("layer", "layer-transit", loader)

    assert len(calls) == 2


def test_redis_failure_falls_back_to_loader_and_marks_degraded():
    failing = CacheStore(FakeRedis(fail=True), l1=_LRU(max_entries=4))

    value = failing.get_or_load("layer", "layer-parcels", lambda: b"payload")

    assert value == b"payload"
    assert "layer" in failing.degraded


def test_l1_respects_ttl():
    lru = _LRU(max_entries=4)
    lru.put("k", b"v")

    assert lru.get("k", ttl_seconds=10) == b"v"
    assert lru.get("k", ttl_seconds=-1) is None


def test_l1_evicts_least_recently_used():
    lru = _LRU(max_entries=2)
    lru.put("a", b"1")
    lru.put("b", b"2")
    lru.get("a", ttl_seconds=10)
    lru.put("c", b"3")

    assert lru.get("b", ttl_seconds=10) is None
    assert lru.get("a", ttl_seconds=10) == b"1"


def test_key_includes_schema_and_content_version():
    key = keys.build("layer", "layer-basemap")

    assert key.startswith(f"cat:{keys.SCHEMA_VERSION}:layer:")
    assert key.endswith(":layer-basemap")
