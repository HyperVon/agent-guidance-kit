from .auth import current_user
from .path_access import read_requested


def get_file(request):
    user = current_user(request)
    if not user:
        return {"status": 401}
    return {"status": 200, "body": read_requested(request.query["name"])}
