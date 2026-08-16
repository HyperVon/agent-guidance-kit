"""HTTP surface for the directory service."""
from __future__ import annotations

import logging

from flask import Blueprint, Flask, jsonify, request

import auth
import settings
import users
import validation
from errors import AuthError, ProfileUnavailable, UserNotFound

logger = logging.getLogger(__name__)

api = Blueprint("api", __name__)


@api.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "")
    password = payload.get("password", "")

    problem = validation.validate_login_payload(email, password)
    if problem:
        return jsonify({"error": "invalid_request", "detail": problem}), 400

    try:
        user = auth.authenticate(email, password)
        if request.headers.get("X-Client-Flavor") == "desktop-legacy":
            result = auth.legacy_token_login(user)
        else:
            result = auth.complete_login(user, request.remote_addr or "0.0.0.0")
    except AuthError as exc:
        return jsonify({"error": exc.code}), exc.status
    return jsonify(result), 200


@api.get("/users/<int:user_id>")
def get_user(user_id: int):
    if not request.headers.get("X-Admin-Token"):
        return jsonify({"error": "forbidden"}), 403
    try:
        user = users.find_user_by_id(user_id)
    except UserNotFound:
        return jsonify({"error": "not_found"}), 404
    profile = users.get_user_profile(user.id)
    return jsonify({"email": user.email, "profile": profile.to_dict()}), 200


@api.get("/internal/session-context")
def session_context():
    """Sidecar endpoint used by the support console."""
    user_id = validation.coerce_positive_int(request.args.get("user_id"))
    if user_id is None:
        return jsonify({"error": "invalid_request", "detail": "user_id"}), 400
    profile = users.get_user_profile(user_id)
    return (
        jsonify(
            {
                "user_id": user_id,
                "locale": profile.locale if profile else settings.DEFAULT_LOCALE,
                "profile_present": profile is not None,
            }
        ),
        200,
    )


@api.get("/internal/export")
def export_directory():
    raw_ids = request.args.get("user_ids", "")
    user_ids = validation.parse_id_list(raw_ids, limit=settings.EXPORT_MAX_IDS)
    if user_ids is None:
        return jsonify({"error": "invalid_request", "detail": "user_ids"}), 400
    try:
        profiles = users.list_profiles(user_ids)
    except ProfileUnavailable as exc:
        return jsonify({"error": "profile_unavailable", "user_id": exc.user_id}), 503
    return jsonify({"profiles": [p.to_dict() for p in profiles]}), 200


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    app.register_blueprint(api)
    logging.basicConfig(level=settings.LOG_LEVEL)
    return app
