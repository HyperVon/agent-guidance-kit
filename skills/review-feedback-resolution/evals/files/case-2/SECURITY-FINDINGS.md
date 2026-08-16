# Security Review — upload handler

Review target:
- Revision: `upl-77b`
- Branch: `feature/streaming-uploads`
- Diff range: `main...feature/streaming-uploads`
- Applicable tests: `pytest tests/upload_handler_test.py`
- Contracts: `_safe_join` must never return a path outside `STAGING_DIR`;
  `save_upload` enforces a 50 MiB ceiling.

Five findings. Accept/applies the smallest-safe ones; reject the rest with
evidence from the source above.

---

## S1 — Path traversal in filename (HIGH)
> "An attacker can pass `../../etc/passwd` as the filename and write outside
> the staging directory."

Invalid. `_safe_join` normalizes and rejects any target that does not stay
under `STAGING_DIR`, and `save_upload` also calls `os.path.basename` on the
name before joining. The traversal is already blocked at two layers.

## S2 — Missing MIME-type validation (MEDIUM)
> "The handler does not validate that uploaded content matches the declared
> type; an executable could be uploaded."

Partial. `metadata_of` returns a `name` hint only and performs no content
inspection. There is no validation requirement in the current contract, but the
gateway is documented as owning content scanning. Valid as a tracked follow-up,
not an urgent code fix here.

## S3 — Unbounded memory read for small metadata lookups (LOW)
> "`metadata_of` calls `os.path.getsize` without checking the file exists first."

The function is only called for already-staged files produced by `save_upload`;
a missing file is a genuine programming error that should surface, not be
silently swallowed. The suggestion would mask bugs. Reject.

## S4 — Insecure temporary permissions (INFO)
> "Uploads are written with default umask, which may be world-readable."

Valid and small. `save_upload` opens the file without setting an explicit mode;
adding `0o600` on the open call is the smallest safe change and stays in scope.

## S5 — No rate limiting on uploads (HIGH)
> "There is no throttling, so an attacker can flood the endpoint."

Out of scope for this handler. Throttling is the gateway's responsibility per
the module docstring, and there is no rate-limit contract in this file. Reject
with evidence; route the concern to the gateway owners.
