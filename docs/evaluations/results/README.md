# Evaluation results — storage and validation

This directory tracks **executed** evaluation runs so the validation matrix can be kept over time.

* Definitions live at `.agents/skills/<name>/evals/evals.json` (structural check only).
* Results live here as machine-readable JSON. Markdown reports in `docs/evaluations/*.md` are sanitized summaries that link to these files. Raw model outputs stay in ignored ephemeral workspaces and are **not** committed.

## File naming

* Multi-skill run (recommended): `YYYY-MM-DD-<model>-<harness>.json` — e.g., `2026-08-11-muse-spark-1.2-contributor-muse-code.json` (harness `muse code`, model `muse-spark-1.2-contributor`).
* Single-skill run: `YYYY-MM-DD-<skill>-<model>-<harness>.json`.

Both shapes are validated. Prefer one aggregated file per harness/model/timestamp covering all skills evaluated together — it keeps the matrix coherent.

## Schema (version 1)

```json
{
  "schema_version": 1,
  "run_id": "2026-08-11-muse-spark-1.2-contributor-muse-code",
  "timestamp": "2026-08-11T23:50:00Z",
  "harness": {"name": "muse code", "version": "0.1.0"},
  "model": {"provider": "meta", "name": "muse-spark-1.2-contributor", "reasoning_effort": "low"},
  "baseline": "no-skill",
  "skills": [
    {
      "skill_name": "bootstrap-project",
      "skill_commit": "c4c79e1",
      "cases": [
        {"id": 1, "kind": "matching", "assertions_total": 4, "skill_pass": 4, "baseline_pass": 0, "better": true},
        {"id": 2, "kind": "neighboring", "assertions_total": 2, "skill_pass": 2, "baseline_pass": 0, "better": true}
      ],
      "overall_better": true,
      "decision": "KEEP"
    }
  ]
}
```

**Rules enforced by `scripts/validate_repository.py`:**

* `schema_version == 1`, `run_id` non-empty, `timestamp` ISO-8601.
* `harness.name`/`model.name` non-empty; `baseline` is `no-skill` or `previous version`.
* `skills[]` non-empty; each `skill_name` must match an existing skill directory and its committed `evals/evals.json`.
* Each `cases[]` entry: `id` matches the committed eval case `id`, `kind` matches, `assertions_total == skill_pass + failures` and equals the committed `assertions` length, `skill_pass`/`baseline_pass` in `[0, assertions_total]`, `better == (skill_pass > baseline_pass)` when `overall_better` is claimed only if at least one meaningful `better=true`.
* `decision` in `KEEP`, `KEEP_PROVISIONAL`, `REVISE`, `MERGE`, `DEFER`, `REJECT`.
* Linked file must exist when referenced from `validation-matrix.md`.

## How to add a run

1. Run each `evals/evals.json` case twice in a **dedicated empty directory** containing only `evals/files/*` (per `skill-evaluation`), once with the skill and once with the baseline, same prompts/tools/network/model.
2. Grade every `assertions` entry with quoted evidence from the output; keep the raw outputs in the ephemeral workspace (not here).
3. Write the JSON above and a sanitized markdown report (no raw outputs, no private fixtures).
4. Update `docs/evaluations/validation-matrix.md` to link the new result file.
5. Run `make check` — the validator will check the JSON and the matrix links.

## Current harness/model identifiers

* Harness: `muse code` (this repository's active coding harness; version from `muse --version` or `0.1.0` if not exposed).
* Model: `muse-spark-1.2-contributor` (`provider: meta`). Record `reasoning_effort` when the harness exposes it (e.g., `low`).

Do not claim `better` or `KEEP` without evidence-graded assertions. One run per condition per model is smoke-level evidence — repeat across models/harnesses before portability claims.
