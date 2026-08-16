"""Dunning: retry schedule for failed charges."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

RETRY_OFFSETS_HOURS = (4, 24, 72, 168)
MAX_ATTEMPTS = len(RETRY_OFFSETS_HOURS)


def next_attempt_at(first_failure_at: datetime, attempt: int) -> Optional[datetime]:
    """Return when attempt number `attempt` (1-based) should run."""
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    if attempt > MAX_ATTEMPTS:
        return None
    return first_failure_at + timedelta(hours=RETRY_OFFSETS_HOURS[attempt - 1])


def should_cancel(attempt: int) -> bool:
    return attempt > MAX_ATTEMPTS


def schedule(first_failure_at: datetime) -> list[datetime]:
    out = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        moment = next_attempt_at(first_failure_at, attempt)
        if moment is not None:
            out.append(moment)
    return out
