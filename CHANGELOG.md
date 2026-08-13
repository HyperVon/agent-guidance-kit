# Changelog

Notable changes to Agent Guidance Kit are recorded here.

## Unreleased

### Added

- `frontend-quality-review` for report-only UI, interaction-state,
  accessibility, responsive, and frontend-quality review.
- `threat-modeling` for explicit repository-grounded design-time threat models,
  distinct from implementation-focused `security-review`.
- Clean-context evaluation definitions for the two new skills and additional
  behavior-specific probes for the approved existing-skill improvements.

### Changed

- Enriched the evidence/verification spine across `ai-slop-detector`,
  `skill-optimizer`, `code-review`, `quality-hardening`, `skill-authoring`,
  `harness-adaptation`, `systematic-debugging`, `security-review`,
  `dependency-upgrade`, `reduce-code-size`, `skill-evaluation`, and
  `catalog-discovery`.
- Updated catalog routing, dependency metadata, README inventory, and public
  provenance for the 2026-08-13 external skill-discovery intake.
- Strengthened evaluation integrity guidance: every new comparison must use
  separate fresh `WITH-SKILL` and `BASELINE` workers or harness sessions with
  verifiable skill loading/absence; role-played baselines are invalid. Workers
  are also blind to the evaluation purpose and receive neutral paths without
  rubric leakage. Actual session cwd/workspace metadata and a visible-file
  manifest are now required; a prompt-mentioned path is not isolation. The
  attempted Luna/Max run that exposed catalog evaluation metadata was rejected
  and not recorded. Harness-level exposure of the target skill's name, path,
  description, catalog entry, or injection metadata is also contamination.
  Historical result files are now documented as provisional until that
  boundary is rerun or evidenced.

### Fixed

- Documentation review corrections: `README.md` skill-count badges and status line
  now read `22/22` (were `20/20`), matching `docs/evaluations/SUMMARY.md` and
  `validation-matrix.md` after the `adversarial-pr-review` and `dependency-upgrade`
  evaluations; the "Included skills" list now covers all 22 catalog skills
  (added `catalog-discovery`, `adversarial-pr-review`, `git-github-workflow`,
  `dependency-upgrade`, `upstream-contribution`) and no longer claims it is the
  "initial" catalog; the validation-matrix link wording no longer calls a
  `2026-08-11` result the "latest" run.

## 1.1.0 - 2026-08-12

### Added

- `install_skills` `plan --diff`/`--check` (skill + routing unified diff, conflict-only check) plus informational `AGENTS.md`/harness entrypoint recommendations surfaced via `--diff` and owned by `harness-adaptation`.
- `harness_recommendations.py` paste-ready thin-pointer recommendations for `AGENTS.md` and harness adapters (`CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, etc.) surfaced in `plan --diff`.
- `validate_repository.py --json` machine-readable output and `related`-skill file-link validation; `validate_evaluation_summary` fresh check for `docs/evaluations/SUMMARY.md`.
- `verify_harness.py` harness probe (`--json`/`--verbose`/`--update`) and Muse Code `BEST_EFFORT` → `VERIFIED` (docs/harness-compatibility.md `2026-08-12`).
- `generate_evaluation_summary.py` and `docs/evaluations/SUMMARY.md` — auto-generated latest-per-skill aggregate (latest per skill×harness×model, 20 skills, 2 result files) with conversational maintenance (human asks agent to “run evals”, agent runs scripts; validated by `make check`).
- Executed evaluations for 3 remaining skills (`catalog-discovery`, `git-github-workflow`, `upstream-contribution`) — `2026-08-12` JSON+MD, now `20/20` evaluated on `muse-spark-1.2-contributor`/`muse code` (xhigh) with `skill-evaluation` conversational docs.
- ADRs `002-requirements-hashing-and-harness-verification` and `003-install-skills-diff-check-and-related-links`.
- GitHub issue forms, a pull request template, community guidance, and Dependabot configuration.
- Repository metadata and security defaults for public collaboration.

### Changed

- `requirements-dev.txt` hash-pinned (`--hash=sha256` for PyYAML 6.0.3, ruff 0.16.2, skills-ref 0.1.1) with `setup_dev.py`/`CI` `--require-hashes`.
- `README.md` harness badge `VERIFIED (muse)`; `docs/design.md` Mermaid flowchart; `docs/roadmap.md` tranche checkboxes; `CONTRIBUTING.md` pre-commit note.
- Agent-facing eval docs now conversational: `skill-evaluation`, `results/README.md`, `validation-matrix.md`, and `SUMMARY.md` state the agent runs `generate_evaluation_summary.py --write` and `make check`; human does not run scripts manually.

## 1.0.0 - 2026-08-10

### Added

- The initial project-local guidance catalog and approval-gated adoption flow.
- Compatibility guidance for supported and capability-compatible agent harnesses.
- Deterministic validation, installation, inventory, and source-resolution tools.
