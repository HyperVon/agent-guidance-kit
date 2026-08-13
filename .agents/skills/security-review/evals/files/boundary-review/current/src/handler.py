from .config import ALLOW_GUESTS, SERVICE_TOKEN


def authorize(request):
    if ALLOW_GUESTS:
        return True
    return request.headers.get("Authorization") == f"Bearer {SERVICE_TOKEN}"
