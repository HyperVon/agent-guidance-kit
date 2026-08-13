from .auth import authenticate


def dispatch(request, handler):
    if authenticate(request):
        return handler(request)
    return {"status": 403}
