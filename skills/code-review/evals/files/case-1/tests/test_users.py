from __future__ import annotations

import pytest

import users
from conftest import connection_factory
from errors import ProfileUnavailable, UserNotFound


def test_find_user_by_email_normalizes_and_returns_user(monkeypatch, user_row):
    conn, factory = connection_factory([user_row])
    monkeypatch.setattr(users, "get_connection", factory)

    user = users.find_user_by_email("  Eval@Example.COM ")

    assert user.id == 4021
    assert user.status == "active"
    sql, params = conn.statements[0]
    assert params == ("eval@example.com",)
    assert "%s" in sql


def test_find_user_by_email_raises_when_absent(monkeypatch):
    _, factory = connection_factory([None])
    monkeypatch.setattr(users, "get_connection", factory)

    with pytest.raises(UserNotFound):
        users.find_user_by_email("missing@example.com")


def test_get_user_profile_materializes_row(monkeypatch, profile_row):
    _, factory = connection_factory([profile_row])
    monkeypatch.setattr(users, "get_connection", factory)

    profile = users.get_user_profile(4021)

    assert profile.display_name == "Directory User"
    assert profile.email == "eval@example.com"
    assert profile.mfa_required is True
    assert profile.locale == "en-GB"


def test_get_user_profile_when_row_missing(monkeypatch):
    _, factory = connection_factory([None])
    monkeypatch.setattr(users, "get_connection", factory)

    assert users.get_user_profile(999999) is None


def test_get_user_profile_when_display_name_null(monkeypatch, profile_row):
    profile_row["display_name"] = None
    _, factory = connection_factory([profile_row])
    monkeypatch.setattr(users, "get_connection", factory)

    assert users.get_user_profile(4021) is None


def test_list_profiles_raises_on_gap(monkeypatch, profile_row):
    _, factory = connection_factory([profile_row, None])
    monkeypatch.setattr(users, "get_connection", factory)

    with pytest.raises(ProfileUnavailable):
        users.list_profiles([4021, 4022])


def test_select_rejects_unknown_column():
    with pytest.raises(ValueError):
        users._select(("user_id", "password_reset_token"), "user_profiles", "user_id")
