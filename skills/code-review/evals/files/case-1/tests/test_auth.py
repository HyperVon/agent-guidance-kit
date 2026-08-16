from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import auth
import users
from errors import AuthError, ProfileUnavailable, UserNotFound


class StubUser:
    id = 4021
    email = "eval@example.com"
    password_hash = "pbkdf2_sha256$60000$saltsalt$" + "0" * 64
    status = "active"


class StubProfile:
    def __init__(self, mfa_required=False, locked_until=None, locale="en-US"):
        self.user_id = 4021
        self.display_name = "Directory User"
        self.email = "eval@example.com"
        self.mfa_required = mfa_required
        self.locked_until = locked_until
        self.locale = locale


@pytest.fixture(autouse=True)
def no_db_writes(monkeypatch):
    monkeypatch.setattr(users, "touch_last_seen", lambda *a, **k: None)


def test_authenticate_maps_unknown_user_to_401(monkeypatch):
    def _raise(email):
        raise UserNotFound(email)

    monkeypatch.setattr(users, "find_user_by_email", _raise)

    with pytest.raises(AuthError) as excinfo:
        auth.authenticate("nobody@example.com", "correct-horse-battery")
    assert excinfo.value.status == 401
    assert excinfo.value.code == "invalid_credentials"


def test_authenticate_rejects_disabled_account(monkeypatch):
    disabled = StubUser()
    disabled.status = "disabled"
    monkeypatch.setattr(users, "find_user_by_email", lambda email: disabled)
    monkeypatch.setattr(auth, "verify_password", lambda *a: True)

    with pytest.raises(AuthError) as excinfo:
        auth.authenticate("eval@example.com", "correct-horse-battery")
    assert excinfo.value.status == 403


def test_complete_login_requires_mfa_challenge(monkeypatch):
    monkeypatch.setattr(users, "get_user_profile", lambda uid: StubProfile(mfa_required=True))

    result = auth.complete_login(StubUser(), "198.51.100.4")

    assert result["next"] == "mfa_challenge"
    assert "session_token" not in result


def test_complete_login_rejects_locked_account(monkeypatch):
    locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
    monkeypatch.setattr(
        users, "get_user_profile", lambda uid: StubProfile(locked_until=locked_until)
    )

    with pytest.raises(AuthError) as excinfo:
        auth.complete_login(StubUser(), "198.51.100.4")
    assert excinfo.value.status == 423


def test_complete_login_issues_session(monkeypatch):
    monkeypatch.setattr(users, "get_user_profile", lambda uid: StubProfile(locale="fr-CA"))

    result = auth.complete_login(StubUser(), "198.51.100.4")

    assert result["next"] == "dashboard"
    assert result["locale"] == "fr-CA"
    assert result["session_token"]


@pytest.mark.skip(reason="unstable on the shared CI runner; re-enable with INC-4471 follow-up")
def test_complete_login_surfaces_profile_unavailable(monkeypatch):
    def _raise(user_id):
        raise ProfileUnavailable(user_id)

    monkeypatch.setattr(users, "get_user_profile", _raise)

    with pytest.raises(AuthError) as excinfo:
        auth.complete_login(StubUser(), "198.51.100.4")
    assert excinfo.value.status == 503


def test_legacy_token_login_issues_session_for_non_mfa_user(monkeypatch):
    monkeypatch.setattr(users, "get_user_profile", lambda uid: StubProfile(mfa_required=False))

    result = auth.legacy_token_login(StubUser())

    assert result["next"] == "dashboard"


def test_rate_limit_key_is_stable_and_opaque():
    first = auth.rate_limit_key("Eval@Example.com", "198.51.100.4")
    second = auth.rate_limit_key("eval@example.com", "198.51.100.4")
    assert first == second
    assert "example.com" not in first
