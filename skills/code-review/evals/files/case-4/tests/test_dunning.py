from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from billing import dunning


def test_schedule_has_four_attempts():
    first = datetime(2024, 6, 1, tzinfo=timezone.utc)
    assert len(dunning.schedule(first)) == 4


def test_attempt_offsets_match_policy():
    first = datetime(2024, 6, 1, tzinfo=timezone.utc)
    assert dunning.next_attempt_at(first, 1) == first + timedelta(hours=4)
    assert dunning.next_attempt_at(first, 4) == first + timedelta(hours=168)


def test_attempt_beyond_cap_returns_none():
    first = datetime(2024, 6, 1, tzinfo=timezone.utc)
    assert dunning.next_attempt_at(first, 5) is None


def test_rejects_non_positive_attempt():
    first = datetime(2024, 6, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        dunning.next_attempt_at(first, 0)


def test_should_cancel_after_cap():
    assert dunning.should_cancel(5) is True
    assert dunning.should_cancel(4) is False
