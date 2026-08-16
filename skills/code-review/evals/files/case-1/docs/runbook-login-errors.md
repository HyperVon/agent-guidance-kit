# Runbook: login error rates

## Alerts

| Alert                        | Threshold          | First action                             |
| ---------------------------- | ------------------ | ---------------------------------------- |
| `login_5xx_rate`             | > 1% over 5 min    | Check `directory-api` logs for tracebacks |
| `login_profile_unavailable`  | > 5/min over 5 min | Check profile backfill job status         |
| `login_401_spike`            | > 20% over 10 min  | Check identity provider status page       |

## Recent incidents

### INC-4471 — login 500s for pre-backfill accounts

Reported by the support console. A subset of accounts created before the
`user_profiles` backfill returned `500` from `POST /login`. Traceback observed
in production logs:

```
Traceback (most recent call last):
  File "app.py", line 34, in login
    result = auth.complete_login(user, request.remote_addr or "0.0.0.0")
  File "auth.py", line 63, in complete_login
    profile = users.get_user_profile(user.id)
  File "users.py", line 101, in get_user_profile
    return _row_to_profile(row)
  File "users.py", line 92, in _row_to_profile
    display_name=row["display_name"].strip(),
TypeError: 'NoneType' object is not subscriptable
```

A second variant appeared for two accounts whose `display_name` was null:

```
AttributeError: 'NoneType' object has no attribute 'strip'
```

Expected behavior per `docs/data-layer.md` is `ProfileUnavailable` → HTTP
`503`, which the support console already renders as "try again shortly".

Follow-up owner: directory team. Tracking: PR #214.

## Escalation

Page the on-call directory engineer via the internal rotation. External
status updates go through the status page at https://status.example.com.
