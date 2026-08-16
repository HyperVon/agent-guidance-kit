"""Retry helper for outbound HTTP calls.

Wraps a callable with bounded exponential backoff. Used by the notification
dispatcher and the webhook client.
"""

import time


def retry(attempts: int, func, *args, **kwargs):
    """Invoke func up to `attempts` times, backing off between failures."""
    delay = 1
    for i in range(attempts):
        try:
            return func(*args, **kwargs)
        except Exception:
            if i == attempts - 1:
                raise
            time.sleep(delay)
            delay = delay * 2
    return None
