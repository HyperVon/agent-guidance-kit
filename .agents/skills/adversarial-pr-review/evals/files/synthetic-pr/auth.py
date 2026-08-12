"""Auth module with intentional reviewable issues for evaluation fixture."""

import os


# Intentional issue: direct use of request parameter without validation (for review)
def authenticate(request):
    token = request.get("token")
    # Risk: no input validation, no rate limiting
    if token == os.environ.get("SECRET_TOKEN"):
        return True
    return False


# Intentional issue: broad exception without logging
def load_user(user_id):
    try:
        return {"id": user_id}
    except Exception:
        pass
