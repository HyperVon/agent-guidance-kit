# API contract

## POST /login

Request body:

```json
{ "email": "user@example.com", "password": "..." }
```

Responses:

| Status | Body                                        | Condition                              |
| ------ | ------------------------------------------- | -------------------------------------- |
| `200`  | `{ "next": "dashboard", "session_token": … }` | Password verified, no MFA required     |
| `200`  | `{ "next": "mfa_challenge", "challenge_id": … }` | Password verified, MFA required     |
| `400`  | `{ "error": "invalid_request", "detail": … }` | Payload failed validation             |
| `401`  | `{ "error": "invalid_credentials" }`        | Unknown address or wrong password      |
| `403`  | `{ "error": "account_disabled" }`           | `users.status != "active"`              |
| `423`  | `{ "error": "account_locked" }`             | `locked_until` in the future            |
| `503`  | `{ "error": "profile_unavailable" }`        | Profile row cannot be materialized      |

The `423` and `mfa_challenge` outcomes are policy gates: every successful
login for an account with `mfa_required = true` must return `mfa_challenge`
before a session token is issued. This holds for both the web client and the
legacy desktop client (`X-Client-Flavor: desktop-legacy`).

Login must never return `500` for a known data condition.

## GET /users/<id>

Requires `X-Admin-Token`. Returns `{ "email": …, "profile": { … } }` or `404`
when the user does not exist, `503` when the profile cannot be materialized.

## GET /internal/session-context

Support-console read path. Returns the effective locale and whether a profile
is present. This endpoint is explicitly tolerant of a missing profile: it
reports `profile_present: false` and falls back to the default locale.

## GET /internal/export

`user_ids` is a comma-separated list, at most `EXPORT_MAX_IDS` entries.
Returns `503` if any requested profile cannot be materialized (the nightly job
retries the whole batch).
