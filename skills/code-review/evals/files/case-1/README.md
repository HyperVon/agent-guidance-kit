# Aperture Directory Service

Internal user directory and login service. Provides:

- `POST /login` — password login for the web client and the legacy desktop client
- `GET /users/<id>` — admin directory lookup
- `GET /internal/session-context` — read-only context for the support console
- `GET /internal/export` — batch profile export for the nightly directory job

## Layout

| Path              | Purpose                                            |
| ----------------- | -------------------------------------------------- |
| `app.py`          | HTTP routes (Flask blueprint)                      |
| `auth.py`         | Password verification, login continuation, sessions |
| `users.py`        | Data access for `users` and `user_profiles`         |
| `validation.py`   | Request payload validation                          |
| `db.py`           | Pooled connection helper                            |
| `settings.py`     | Environment configuration                           |
| `errors.py`       | Shared domain error types                           |
| `docs/`           | API and data-layer contracts, runbooks              |
| `tests/`          | pytest suite                                        |

## Local checks

```
python -m pytest -q
python -m ruff check .
```

The test suite stubs the database; no live Postgres is required.

## Data model note

`users` rows were created continuously since the first release. The
`user_profiles` table was introduced later and backfilled in batches, so a
small number of older `users` rows have no matching `user_profiles` row. The
nightly reconciliation job reports the remaining gap.
