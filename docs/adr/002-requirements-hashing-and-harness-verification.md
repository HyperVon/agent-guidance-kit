# ADR 002 — Requirements hashing and harness verification

Date: 2026-08-12
Status: Accepted
Branch: feat/roadmap-comprehensive-improvements

## Context

`requirements-dev.txt` pinned versions but no hashes, leaving `pip install` without supply-chain verification. The kit also lacked a harness verification probe for Muse Code, which remained `BEST_EFFORT` in `docs/harness-compatibility.md` despite being the active development harness. Tranche 2 items F5 and 2E required both.

## Decision

- **F5** — Replace `requirements-dev.txt` with hash-pinned entries (`--hash=sha256:...` for every sdist/wheel of PyYAML 6.0.3, ruff 0.16.2, skills-ref 0.1.1, generated from `https://pypi.org/pypi/<pkg>/<ver>/json` on 2026-08-12). Update `scripts/setup_dev.py` to detect `--hash=` and pass `--require-hashes`, and update `.github/workflows/check.yml` to `pip install --require-hashes -r requirements-dev.txt`. Hashes cover all platforms; verification is `pip install --require-hashes --dry-run`.

- **2E** — Enhance `scripts/verify_harness.py` with `--json`, `--verbose`, and `--update` flags, plus `verify_current_harness()` checks for canonical hierarchy, harness entrypoints, and skill catalog. Probe run under Muse Spark (`muse`) now marks the harness `VERIFIED` and updates `docs/harness-compatibility.md` snapshot date to `2026-08-12` with row `| Muse Code | \`AGENTS.md\` hierarchy | Native (\`.agents/skills/\`) | canonical files directly | VERIFIED |`.

- Record both as `SCHEMA_VERSION` unchanged (still `1`/`2` where applicable); no skill-dependencies schema bump. Future `SCHEMA_VERSION` bumps will get dedicated ADRs per ADR 001.

## Consequences

- `make check` and CI now enforce hash verification; Dependabot updates must regenerate hashes.
- `verify_harness.py --harness muse --json` provides machine-readable evidence; `--update` keeps `harness-compatibility.md` in sync.
- Muse Code moves `BEST_EFFORT` → `VERIFIED`, reflecting actual session evidence.
