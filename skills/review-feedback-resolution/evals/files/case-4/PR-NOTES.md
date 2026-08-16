# PR Notes — outbound retry changes

Branch: `feature/retry-backoff`
Revision: `rt-9012`
Applicable tests: `pytest tests/retry_test.py`

Mixed notes from the team. Some are about the current change; some are new
requests that go beyond this diff.

## Team note A (retry loop is wrong)
> "The retry loop caps at `attempts` total calls but `retry` can return `None`
> on a path that already raised — it swallows the final error instead of
> re-raising."

This is genuine review feedback on the current change. `retry` is supposed to
re-raise on the final attempt, but the `return None` after the loop is dead code
that implies a swallowed failure. It is in scope for this PR.

## Team note B (retry loop is wrong)
> "Backoff uses `delay = delay * 2` with no ceiling, so a high `attempts`
> value sleeps for hours."

Also in-scope review feedback on the current change: unbounded exponential
backoff is a real defect. A max ceiling is the smallest safe fix.

## Team note C (new feature)
> "We should add rate limiting as a new feature so callers can't exceed their
> quota when retrying."

This is a new-feature request, not a comment on the existing retry change. It
introduces new behavior (a token bucket / limiter) that is out of scope for this
diff and has no contract in `retry_module.py`.

## Team note D (new feature, same as C)
> "Add a configurable rate limiter to the retry helper."

Restates note C. It is a feature request, not review feedback on the current
code, and belongs in its own planning item rather than this resolution pass.
