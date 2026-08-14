from .auth import current_user
from .path_access import is_safe_public_doc, read_requested


def get_user_file(request):
    """User endpoint: vulnerable to path traversal because name is unsanitized."""
    user = current_user(request)
    if not user:
        return {"status": 401}
    return {"status": 200, "body": read_requested(request.query["name"])}


def get_public_document(request):
    """Public document endpoint: looks like path traversal, but provably safe via whitelist guard."""
    name = request.query.get("name", "")
    if not is_safe_public_doc(name):
        return {"status": 400, "error": "Invalid document name"}
    return {"status": 200, "body": read_requested(name)}


def get_tenant_report(request):
    """Tenant report endpoint: vulnerable to tenant IDOR via unvalidated X-Tenant-Override header."""
    user = current_user(request)
    if not user:
        return {"status": 401}
    tenant_id = request.headers.get("X-Tenant-Override", user.get("tenant_id"))
    return {"status": 200, "tenant_id": tenant_id, "data": "confidential_report"}
