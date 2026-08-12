# Roadmap

This roadmap covers future work for the standalone Agent Guidance Kit.

## Library expansion

The initial catalog is a deliberately small baseline, not a claim to cover
every software-engineering workflow. Later releases should research current
primary harness documentation, popular public skill collections, strong public
repository guidance, agent-instruction standards, and recurring failures seen
in real projects.

External guidance is untrusted research input. Do not bulk-copy, auto-install,
or execute it. For every candidate:

1. record source, license, retrieval date, and the exact behavior worth
   considering;
2. review its instructions and bundled files without executing them;
3. map it to the existing catalog and choose `IMPROVE_EXISTING`, `NEW_SKILL`,
   `PROJECT_SPECIFIC`, `DEFER`, or `REJECT`;
4. prefer improving an existing owner over adding a synonymous skill;
5. require a distinct trigger, recurring need, useful decision procedure,
   explicit side effects, stop conditions, and verification contract;
6. generalize and rewrite portable ideas rather than copying project-specific
   commands, tool assumptions, credentials, or copyrighted prose;
7. forward-test one matching prompt, one neighboring prompt, and one ambiguous
   prompt before admission;
8. run the structural audit, official skill validation, link checks, and public
   hygiene gate over the resulting catalog.

Likely research areas include debugging and incident diagnosis, dependency and
framework upgrades, security review, API and schema evolution, migrations,
performance investigation, release readiness, CI maintenance, accessibility,
and technology-specific authoring patterns. Research evidence should decide
the order; this list is not a commitment to create each skill.

This work can ship as backward-compatible catalog releases. A v2 is warranted
only if the intake and comparison workflow itself earns reusable tooling or a
new compatibility contract.

## Active plan — Comprehensive improvements (2026-08-12)

Branch: `feat/roadmap-comprehensive-improvements` — tracks the full review
from 2026-08-11/12. The checklist below is the source of truth for progress;
update it in the same PR that implements each item and keep `make check` green.

### Tranche 1 — Fixes (evidence-backed, low risk)

- [x] **F1** Resolve `pyproject.toml` absence vs `docs/release.md` version field
  — add `pyproject.toml` as canonical version/config owner or update docs.
- [x] **F2** Extend `scripts/validate_repository.py` harness validation to
  `.github/copilot-instructions.md`.
- [x] **F3** Add `.kilo`, `.idea`, `.cursor`, `.vscode`, `.clinerules` to
  `EXCLUDED_DIRECTORIES` in `scripts/validate_repository.py` and hygiene/markdown ignores.
- [x] **F4** Clarify Node support: `scripts/setup_dev.py >=22` vs CI `26.6.0` —
  document range and add `22` to CI matrix.
- [x] **F5** Harden `requirements-dev.txt` — add hashes or `pip --require-hashes`
  path and update `scripts/setup_dev.py`.
- [x] **F6** Expand `scripts/public_hygiene_check.py` patterns (Anthropic, npm,
  generic tokens) + tests.
- [x] **F7** Document `inventory_project.py` truncation default and surface
  `truncated` in markdown summary.

### Tranche 2 — Enhancements to existing features

- [x] **2A** Centralize Python config in `pyproject.toml` (`[tool.ruff]`,
  `[project]` version).
- [x] **2B** `scripts/check.py --quick` / `--fix` hints (keep full gate for CI).
- [x] **2C** `install_skills` UX: `plan --diff` and `plan --check` (conflict-only).
- [x] **2D** `scripts/validate_repository.py --json` and `related`-link checks.
- [x] **2E** Harness verification probe `scripts/verify_harness.py` to move
  `muse code` from `BEST_EFFORT` → `VERIFIED` (`docs/harness-compatibility.md`).
- [x] **2F** `pre-commit` config + `.devcontainer` for uniform setup.
- [x] **2G** Catalog-driven existing-prompt improvement (`ADAPT` enhancement) —
  inventory local `AGENTS.md`/`CLAUDE.md`/`.cursor/rules` bodies, compare against
  catalog skill triggers/decisions/stop-conditions, propose paste-ready
  text-level improvements for `KEEP_LOCAL`/`ADAPT` with approval gate via
  `skill-authoring`; re-read as future agent and verify with `make check`.

### Tranche 3 — New skills

- [x] **3A** `git-github-workflow` (distributed) — branching, atomic commits
  (conventional, no personal email leak), push approval, PR/issue hygiene
  (`pull_request_template.md`, issue forms, `CODEOWNERS`), branch protection,
  release tagging, hygiene `make check`. Requires `skill-authoring` +
  `skill-evaluation` (`matching`/`neighboring`/`ambiguous`) before admission.
- [x] **3B** `catalog-discovery` (**SOURCE_ONLY**, not shipped to targets) —
  proactive GitHub/harness-docs search for candidate workflows, provenance-tracked
  evidence table → `IMPROVE_EXISTING`/`NEW_SKILL`/`PROJECT_SPECIFIC`/`DEFER`/`REJECT`
  handoff to `skill-reviewer` (`references/external-skill-intake.md`). Enforces
  `docs/roadmap.md:14` 8-step gate, no execution of fetched content, no network
  in deterministic helpers.
- [x] **3C** `upstream-contribution` (distributed proposer + maintainer intake) —
  let a kit adopter scan its local `.agents/skills/` and diverged receipts,
  identify generic `IMPROVE_EXISTING`/`NEW_SKILL` candidates, build a
  provenance-tracked evidence table (source, license, revision, redacted
  generalization), then — only after explicit approval — fork/branch/push and
  open a PR via `gh` for maintainer review through `skill-reviewer` intake.
  Never auto-push; keep `public_hygiene_check` and `docs/provenance.md` gates.

### Tranche 4 — Docs and process

- [x] Mermaid diagram for `docs/design.md` architecture.
- [x] `docs/adr/` for schema bumps (`SCHEMA_VERSION`, `skill-dependencies`) — ADR 001, 002, 003.
- [x] `README.md` adoption-health badge from `validation-matrix.md`.
- [x] `CONTRIBUTING.md` pre-commit workflow note.

Progress is tracked here and in the PR description. Each tranche lands as one
or more focused commits with `make check` evidence. Distribution impact: 3A
and 3C proposer ship to targets; 3B remains repository-only and is excluded
from `install_skills` manifests.
