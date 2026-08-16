"""Post-deploy cache warmup."""
from __future__ import annotations

import logging
from typing import Callable, Iterable

from cache.store import CacheStore

logger = logging.getLogger(__name__)


def warm(
    store: CacheStore,
    namespace: str,
    entity_ids: Iterable[str],
    loader: Callable[[str], bytes],
) -> int:
    warmed = 0
    for entity_id in entity_ids:
        store.get_or_load(namespace, entity_id, lambda eid=entity_id: loader(eid))
        warmed += 1
    logger.info("warmup complete namespace=%s count=%d", namespace, warmed)
    return warmed
