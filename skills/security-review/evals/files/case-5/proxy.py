"""Image proxy endpoint.

Fetches a remote image by URL and streams it back to the client after a small
transform. Used by the marketing site to normalize third-party assets.
"""

import urllib.request

from flask import Blueprint, request, Response

proxy_bp = Blueprint("proxy", __name__)

MAX_BYTES = 5 * 1024 * 1024


@proxy_bp.route("/api/image-proxy", methods=["GET"])
def image_proxy():
    target = request.args.get("url", "")
    if not target:
        return {"error": "missing url"}, 400

    # Accept the caller-supplied URL and fetch it server-side. The host is not
    # restricted to allowed origins.
    req = urllib.request.Request(target)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = resp.read(MAX_BYTES)

    content_type = resp.headers.get("Content-Type", "application/octet-stream")
    return Response(data, mimetype=content_type)
