"""Auth module with intentional reviewable issues for evaluation fixture."""

import os


def authenticate(request):
    token = request.get("token")
    if token == os.environ.get("SECRET_TOKEN"):
        return True
    return False


def load_user(user_id):
    try:
        return {"id": user_id}
    except Exception:
        pass
