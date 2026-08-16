# Data-layer contract

Applies to `users.py`. This document is the source of truth for the read paths
consumed by `auth.py` and `app.py`.

## Lookup functions

| Function              | Success                | Absent record            | Unusable record        |
| --------------------- | ---------------------- | ------------------------ | ---------------------- |
| `find_user_by_email`  | `User`                 | raises `UserNotFound`    | raises `UserNotFound`  |
| `find_user_by_id`     | `User`                 | raises `UserNotFound`    | raises `UserNotFound`  |
| `get_user_profile`    | `Profile`              | raises `ProfileUnavailable` | raises `ProfileUnavailable` |
| `list_profiles`       | `list[Profile]`        | raises `ProfileUnavailable` | raises `ProfileUnavailable` |

### `get_user_profile`

Returns a fully materialized `Profile`. A profile is *unusable* when the
`user_profiles` row is missing (pre-backfill user) or when a `NOT NULL`
expectation is violated by legacy data — for example a null `display_name` or
`email`.

`get_user_profile` must signal both conditions with `ProfileUnavailable`.
Callers distinguish "this user cannot be served right now" (`503`) from "this
user does not exist" (`404`), and the MFA gate in `auth.py` depends on
receiving a real `Profile` rather than a placeholder. A sentinel return value
(`None`, empty `Profile`, or default-filled `Profile`) is not an acceptable
substitute, because a caller that treats a falsy profile as "no MFA required"
would silently downgrade the login policy.

### Error taxonomy

- `UserNotFound` maps to HTTP `404` (or `401` on the login path, so login does
  not confirm account existence).
- `ProfileUnavailable` maps to HTTP `503`. It is a retryable condition and is
  paged when the rate exceeds 5/minute (see `docs/runbook-login-errors.md`).

## Write paths

`touch_last_seen` is best-effort and runs inside the caller's connection
context. It must not raise into the login response path.
