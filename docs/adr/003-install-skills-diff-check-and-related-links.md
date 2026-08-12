# ADR 003 — install_skills --diff/--check and related-link validation

Date: 2026-08-12
Status: Accepted
Branch: feat/roadmap-comprehensive-improvements

## Context

`install_skills` planning required writing a plan file before seeing changes, slowing inner loop. `validate_repository.py` lacked machine-readable output and explicit `related`-skill link checks, while `bootstrap-project` covered skills but surfaced little about `AGENTS.md` / harness entrypoints (`CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`).

## Decision

- **2C** — Add `plan --diff` (unified diff of skill files + managed `AGENTS.md` routing block) and `plan --check` (conflict-only, no file write, exit 1 on `CONFLICT`/`ASK`) to both `apply.py` and `__main__.py`. Implement `generate_diff()` / `print_diff()` with `difflib.unified_diff`, plus harness recommendations (informational notes when harness files exist without canonical reference, directing to `harness-adaptation`). Document in `bootstrap-project/SKILL.md`.

- **2D** — Add `scripts/validate_repository.py --json` (emits `{errors, valid, skills_validated, ...}`) and `validate_related_links()` that rejects relative file links to `related` skills (`related skill 'x' must not be linked via relative path; use plain reference`). Keep existing `requires` link check; `related` is now explicitly validated.

- **Harness / AGENTS.md extension** — `--diff` harness notes and `harness-adaptation` remain the owners for `AGENTS.md` hierarchy upgrades; skill plan stays receipt-aware and never auto-edits harness files without approval. This satisfies the request to surface `AGENTS.md` and harness file recommendations alongside skill diffs.

## Consequences

- `install_skills plan --diff --check` enables fast CI/conflict checks without temp files.
- `validate_repository.py --json` supports tooling/parsing; related-link rule prevents broken selective installs.
- Harness file guidance is surfaced but not auto-applied, preserving approval gate.
