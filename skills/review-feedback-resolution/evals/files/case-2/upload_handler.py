"""File upload handler.

Accepts multipart uploads, streams them to a staging directory, and returns a
handle the caller can later commit. Intentionally simple: large-file streaming
and quota enforcement are handled by the gateway in front of this service.
"""

import os

STAGING_DIR = "/var/staging/uploads"


def _safe_join(base: str, name: str) -> str:
    """Join name onto base, refusing to escape the base directory."""
    target = os.path.normpath(os.path.join(base, name))
    if not target.startswith(base + os.sep) and target != base:
        raise ValueError("path escapes staging directory")
    return target


def save_upload(filename: str, payload: bytes) -> str:
    """Persist an upload and return its staging path."""
    if not filename:
        raise ValueError("filename is required")
    if len(payload) > 50 * 1024 * 1024:
        raise ValueError("payload exceeds 50 MiB limit")
    path = _safe_join(STAGING_DIR, os.path.basename(filename))
    with open(path, "wb") as handle:
        handle.write(payload)
    return path


def metadata_of(filename: str) -> dict:
    """Return size and type hints for a staged upload."""
    path = _safe_join(STAGING_DIR, os.path.basename(filename))
    return {
        "size": os.path.getsize(path),
        "name": os.path.basename(filename),
    }
