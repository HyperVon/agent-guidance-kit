from src.auth import authenticate


def test_admin_header_is_allowed():
    request = type("Request", (), {"headers": {"X-User": "alice", "X-Role": "admin"}})()
    assert authenticate(request) is True
