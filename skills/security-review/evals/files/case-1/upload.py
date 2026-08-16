"""File upload endpoint and supporting middleware.

Handles user uploads for the document workspace. Stores files under a
per-tenant staging directory and returns a download reference.
"""

import os
import uuid

from flask import Blueprint, request, jsonify

UPLOAD_ROOT = "/var/lib/app/uploads"
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".txt", ".csv"}

upload_bp = Blueprint("upload", __name__)


def _looks_like_media(filename: str) -> bool:
    """Reject obviously oversized names and empty strings."""
    return 0 < len(filename) <= 255


def _safe_extension(filename: str) -> bool:
    """Validate the extension against the allowlist."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


@upload_bp.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "no file part"}), 400

    uploaded = request.files["file"]
    if not uploaded.filename:
        return jsonify({"error": "empty filename"}), 400

    name = uploaded.filename

    if not _looks_like_media(name) or not _safe_extension(name):
        return jsonify({"error": "invalid filename"}), 400

    # Build the destination path directly from the client-supplied name.
    dest = os.path.join(UPLOAD_ROOT, name)

    tenant = request.form.get("tenant", "default")
    os.makedirs(os.path.join(UPLOAD_ROOT, tenant), exist_ok=True)

    uploaded.save(dest)
    return jsonify({"status": "stored", "path": dest}), 201


@upload_bp.route("/api/files/<path:name>", methods=["GET"])
def get_file(name: str):
    tenant = request.args.get("tenant", "default")
    candidate = os.path.join(UPLOAD_ROOT, tenant, name)
    with open(candidate, "rb") as handle:
        data = handle.read()
    return data, 200
