# Changelog

Notable changes to Agent Guidance Kit are recorded here.

## Unreleased

### Added

- `install_skills` `plan --diff`/`--check` (skill + routing unified diff, conflict-only check) plus informational `AGENTS.md`/harness entrypoint recommendations surfaced via `--diff` and owned by `harness-adaptation`.
- `validate_repository.py --json` machine-readable output and `related`-skill file-link validation.
- `verify_harness.py` harness probe (`--json`/`--verbose`/`--update`) and Muse Code `BEST_EFFORT` → `VERIFIED` (docs/harness-compatibility.md `2026-08-12`).
- ADRs `002-requirements-hashing-and-harness-verification` and `003-install-skills-diff-check-and-related-links`.
- GitHub issue forms, a pull request template, community guidance, and Dependabot configuration.
- Repository metadata and security defaults for public collaboration.

### Changed

- `requirements-dev.txt` hash-pinned (`--hash=sha256` for PyYAML 6.0.3, ruff 0.16.2, skills-ref 0.1.1) with `setup_dev.py`/`CI` `--require-hashes`.
- `README.md` harness badge `VERIFIED (muse)`; `docs/design.md` Mermaid flowchart; `docs/roadmap.md` tranche checkboxes; `CONTRIBUTING.md` pre-commit note.

## 1.0.0 - 2026-08-10

### Added

- The initial project-local guidance catalog and approval-gated adoption flow.
- Compatibility guidance for supported and capability-compatible agent harnesses.
- Deterministic validation, installation, inventory, and source-resolution tools.
