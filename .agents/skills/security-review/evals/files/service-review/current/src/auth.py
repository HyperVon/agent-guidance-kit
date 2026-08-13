def current_user(request):
    return request.headers.get("X-User")
