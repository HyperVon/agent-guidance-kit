"""Shared stubs. The suite never touches a real database."""
from __future__ import annotations

import contextlib
from datetime import datetime, timezone

import pytest


class FakeResult:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row

    def fetchall(self):
        return [] if self._row is None else [self._row]


class FakeConnection:
    """Records statements and replays a scripted row per call."""

    def __init__(self, rows):
        self._rows = list(rows)
        self.statements: list[tuple[str, tuple]] = []
        self.committed = False
        self.rolled_back = False

    def execute(self, sql, params=()):
        self.statements.append((sql, params))
        row = self._rows.pop(0) if self._rows else None
        return FakeResult(row)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def connection_factory(rows):
    conn = FakeConnection(rows)

    @contextlib.contextmanager
    def _get_connection():
        yield conn

    return conn, _get_connection


@pytest.fixture
def user_row():
    return {
        "id": 4021,
        "email": "eval@example.com",
        "password_hash": "pbkdf2_sha256$60000$saltsalt$" + "0" * 64,
        "status": "active",
        "created_at": datetime(2021, 3, 4, tzinfo=timezone.utc),
    }


@pytest.fixture
def profile_row():
    return {
        "user_id": 4021,
        "display_name": " Directory User ",
        "email": "EVAL@EXAMPLE.COM",
        "mfa_required": True,
        "locked_until": None,
        "locale": "en-GB",
    }
