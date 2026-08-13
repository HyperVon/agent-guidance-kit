from src.api import render_user


def test_response_is_successful():
    response = render_user(type("User", (), {"name": "A", "active": True})())
    assert response["active"] is True
