"""Configuration loading for the cache layer."""
from __future__ import annotations

import functools
import os
from typing import Any

import yaml

CONFIG_PATH = os.environ.get("CACHE_CONFIG_PATH", "config/cache.yaml")


@functools.lru_cache(maxsize=1)
def cache_config() -> dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)
