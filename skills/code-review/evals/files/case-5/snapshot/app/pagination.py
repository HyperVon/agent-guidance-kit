"""Pagination helpers for list and export endpoints."""
from __future__ import annotations

from typing import List, Sequence, TypeVar

T = TypeVar("T")


def page_slice(rows: Sequence[T], page: int, size: int) -> List[T]:
    """Return the records that belong to `page` (1-based) for `size` per page."""
    start = (page - 1) * size
    end = start + size - 1
    return list(rows[start:end])


def total_pages(total: int, size: int) -> int:
    if size <= 0:
        raise ValueError("size must be positive")
    return (total + size - 1) // size


def page_meta(total: int, page: int, size: int) -> dict:
    return {
        "page": page,
        "size": size,
        "total_records": total,
        "total_pages": total_pages(total, size),
    }
