# Ledgerline payments gateway

Public API edge for the payments platform. Terminates client requests,
authenticates bearer tokens, and forwards authorized calls to the ledger.

## Layout

| Path                        | Purpose                                             |
| --------------------------- | --------------------------------------------------- |
| `service/app.py`            | Routes (`/v1/payments`, `/v1/refunds`, `/v1/tokens`) |
| `service/auth.py`           | Bearer-token middleware and scope checks             |
| `service/token.py`          | Access/refresh token issuance for mesh clients        |
| `service/keys.py`           | JWKS fetch, cache, and signing-key resolution         |
| `service/ledger.py`         | Ledger reads and refund writes (trimmed)              |
| `service/settings.py`       | Environment configuration                             |
| `docs/auth-contract.md`     | Approved authentication contract                      |
| `patches/`                  | Exported diff for the change under review             |
| `tests/`                    | pytest suite                                          |

## Review snapshot

The working tree is at the tip of `security/tighten-token-validation`. The
exported diff for the change is
`patches/0007-tighten-token-validation.patch`. No `.git` directory, CI log, or
test output was captured with this snapshot, and dependencies are not
installed in the review workspace.

## Local checks

```
pip install -r requirements.txt
PYTHONPATH=service python -m pytest -q
python -m ruff check .
```

## Runtime notes

- Deployed behind the mesh ingress; `/v1/tokens` is reachable only from mesh
  clients listed in `MESH_CLIENTS`.
- `Authorization` headers arrive from the public internet on all `/v1/*`
  resource routes.
- Key material is mounted by the platform at the path in
  `JWT_PRIVATE_KEY_PATH`; the rollout to the EU cluster is still in progress.
