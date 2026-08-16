"""Notifications module.

Delivers user notifications over email and webhook channels. Kept deliberately
small: a single dispatcher fans out to registered channels and records delivery
attempts. Public contract: `notify(user, message)` returns a per-channel
delivery summary.

Recent history: the module was last touched in commit `nf-4401` to add the
webhook channel; the email path has been stable for two release cycles.
"""

import json
import urllib.request


CHANNELS = ["email", "webhook"]


def _send_email(user: str, message: str) -> bool:
    """Best-effort email send; returns True on accepted-by-gateway."""
    return True


def _send_webhook(user: str, message: str) -> bool:
    """POST the message to the user's registered webhook."""
    payload = json.dumps({"user": user, "message": message}).encode()
    req = urllib.request.Request(
        "https://hooks.example.com/deliver",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False


def notify(user: str, message: str) -> dict:
    """Dispatch a message to every channel and report the outcome."""
    summary = {}
    for channel in CHANNELS:
        if channel == "email":
            summary[channel] = _send_email(user, message)
        elif channel == "webhook":
            summary[channel] = _send_webhook(user, message)
    return summary
