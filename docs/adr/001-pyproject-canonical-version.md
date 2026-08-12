# ADR 001 — pyproject.toml as canonical version and tool config

Date: 2026-08-12
Status: Accepted
Branch: feat/roadmap-comprehensive-improvements

## Context

`docs/release.md` described `pyproject.toml` as the version source, but the
repository had only `package.json` and `requirements-dev.txt`. `pyproject.toml`
is the standard Python project metadata file and the central place for `[tool.*]`
config (ruff, build-system). Without it, `make check` relied on implicit defaults
and `docs/release.md` was inaccurate.

## Decision

Add `pyproject.toml` with:

- `[project]` `name = "agent-guidance-kit"`, `version = "1.0.0"` (matches `package.json`)
- `[tool.ruff]` `line-length = 88`, `target-version = py311`, `select = ["E","F"]`
- `[tool.ruff.lint.mccabe]` `max-complexity = 50`
- `[build-system]` `setuptools`

Keep `package.json` for Node tooling; `pyproject.toml` is the Python source of
truth. Future schema bumps (install plan `SCHEMA_VERSION`, skill-dependencies
`schema_version`) will be recorded as separate ADRs.

## Consequences

- `make check` now validates against explicit ruff config; no formatting drift.
- `docs/release.md` is now accurate; version bump touches `pyproject.toml`.
- Dependabot `pip` can read `pyproject.toml` alongside `requirements-dev.txt`.
