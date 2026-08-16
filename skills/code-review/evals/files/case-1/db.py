"""Connection helper around the pooled Postgres driver."""
from __future__ import annotations

import contextlib
import logging
import threading
from typing import Iterator

import settings

logger = logging.getLogger(__name__)

_pool_lock = threading.Lock()
_pool = None


def _build_pool():
    # Imported lazily so unit tests can run without the driver installed.
    import psycopg_pool

    return psycopg_pool.ConnectionPool(
        conninfo=settings.database_url(),
        min_size=settings.DB_POOL_MIN,
        max_size=settings.DB_POOL_MAX,
        timeout=settings.DB_CONNECT_TIMEOUT_SECONDS,
    )


def pool():
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = _build_pool()
        return _pool


@contextlib.contextmanager
def get_connection() -> Iterator["Connection"]:
    conn = pool().getconn(timeout=settings.DB_CONNECT_TIMEOUT_SECONDS)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool().putconn(conn)
