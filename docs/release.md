# Release process

This document describes how to version, gate, and cut a release for Agent
Guidance Kit. Release timing and publishing are user-owned decisions — do not
make publication, tagging, or release the automatic next step merely because
a candidate is ready.

## Versioning

* Project version: `pyproject.toml` version field. This is the human-visible
  release version.
* Skill dependency schema: `.agents/skill-dependencies.json` `schema_version`
  (currently `1`). Bump when the catalog shape or dependency contract changes.
* Install plan schema: `.agents/skills/bootstrap-project/scripts/install_skills/constants.py`
  `SCHEMA_VERSION` (currently `2`). Bump when the plan payload, receipt shape,
  or validation rules change. Both writer and validator must agree on the
  schema version.

When bumping either schema:

1. Update the constant and any migration/validation logic.
2. Update `docs/design.md` and `CHANGELOG.md` if the change is user-visible.
3. Run the full gate (`make check`) and ensure existing receipts/plans fail
   closed with a clear error when the version is mismatched.

## Pre-release gate

Run from the repository root:

```text
make check
# or equivalently
python scripts/check.py
```

`scripts/check.py` must end with `All checks passed!` and the unittest
discovery must report `OK`. The gate validates:

* Markdown lint (`markdownlint-cli2`) — 0 issues.
* All skills validate (`agentskills validate .agents/skills/*`).
* Ruff check + format clean.
* Deterministic script tests (`tests/`).
* Repository validation + public hygiene (`scripts/validate_repository.py`,
  `scripts/public_hygiene_check.py`).

The gate requires a development environment. If `markdownlint` or
`agentskills` are missing:

```text
python scripts/setup_dev.py
```

This builds `.venv` (Python 3.14) with the declared dev dependencies. Do not
bypass the gate.

## How to cut a release

1. **Pick the version** — decide the next `pyproject.toml` version (SemVer).
   Update `CHANGELOG.md` with the release notes: added/changed/fixed skills,
   schema bumps, and any migration notes.

2. **Update version metadata** — bump `pyproject.toml`, and if applicable
   `skill-dependencies.json` `schema_version` or `constants.py`
   `SCHEMA_VERSION`.

3. **Run the gate** — `make check` must pass clean. Address findings rather
   than skipping. Report skipped optional tooling as skipped, never passed.

4. **Tag locally (optional)** — `git tag vX.Y.Z` after the gate passes. Do
   not push the tag until the user explicitly authorizes publishing.

5. **Publish only when authorized** — do not create a remote, push, or open
   a pull request unless the user explicitly authorizes that external action.
   Repository visibility and public-release timing are user-owned decisions
   per `.agents/AGENTS.md`.

## Upgrade path for existing adopters

Targets that installed an earlier kit (e.g., `new-kraken-rebalancer` at
`4f3cd82`, receipts `schema_version 2`) upgrade via `agent-guidance-maintenance`:

```text
python .agents/skills/agent-guidance-maintenance/scripts/resolve_source.py resolve --target .
# If you explicitly want the latest kit, first refresh the source checkout (clean main only):
#   git -C /path/to/agent-guidance-kit fetch origin main && git -C /path/to/agent-guidance-kit pull --ff-only origin main
python -c "import sys; sys.path.insert(0, '.agents/skills/bootstrap-project/scripts'); import install_skills, pathlib; print(install_skills.build_plan(pathlib.Path('/path/to/agent-guidance-kit'), pathlib.Path('.'), ['agent-guidance-maintenance','security-review','systematic-debugging']))"
# Or use the maintenance skill workflow: it inspects receipts, detects UPDATE vs UNCHANGED,
# and presents the exact plan with approval gate. Apply only the unchanged plan with --approve.
```

* `UPDATE` is expected for `agent-guidance-maintenance` after `52bd05b` (wrapper + `install_skills/` package, `resolve_source.py` canonical validator) — the installer detects `source_digest != target_digest` and refreshes atomically. `security-review`/`systematic-debugging` remain `UNCHANGED` if their digests match.
* Local project skills (e.g., Kraken's `code-review`, `ai-slop-detector`) are not receipt-owned — the installer leaves them untouched and reports `CONFLICT` if you request a kit skill that collides with a local same-named skill; resolve by `KEEP_LOCAL` or rename.
* `evals/` and `docs/` are `SOURCE_ONLY`/`TRANSIENT` — never copied to targets, so new `validation-matrix.md` or `docs/release.md` changes do not create drift.
* The kit now validates `docs/evaluations/results/*.json` and `validation-matrix.md` links — run `make check` after the upgrade to confirm `1 file(s) validated` and no broken links. If `harness-compatibility` or other docs links were outside the portable catalog (fixed in `bootstrap-project/references/harness-integration.md`), the previous kit would have failed `validate_declared_links` for `bootstrap-project`; the fix makes that skill installable again.

## After a release

* Verify the tag is reachable (`git show vX.Y.Z`).
* Confirm the release artifact (if any) contains only the intended
  `.agents/` and `docs/` content and passes `make check` on a clean checkout.
