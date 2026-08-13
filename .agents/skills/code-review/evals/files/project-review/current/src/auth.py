def authenticate(request):
    user = request.headers.get("X-User")
    if not user:
        return False
    request.user = user
    return request.headers.get("X-Role") == "admin"
