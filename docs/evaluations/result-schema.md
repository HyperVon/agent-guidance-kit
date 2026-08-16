# Evaluation result schema

Committed result files live under `docs/evaluations/results/<skill>.md`. They are
sanitized summaries: keep enough quoted evidence to justify every assertion
decision, but store raw worker outputs, session logs, and tool trajectories in
the ignored local run-evidence directory (see `.gitignore`), not in Git.

A result file MUST contain, per case, the fields below. The
`scripts/validate_evaluations.py` validator enforces the required metadata so a
protocol-invalid run cannot automatically generate a validated checkmark.

## Required top-level metadata

- `skill` — skill name (matches `evals.json` `skill_name`).
- `evaluation_mode` — `routing` or `execution` (or both, in separate sections).
- `method` — how the guided condition was activated: `harness-routing`,
  `harness-injection`, or `prompt-injection-approximation`.
- `case_revision` — commit hash / content hash of the `evals.json` used.
- `fixture_revision` — commit hash / content hash of the fixture used (or
  `designed_only`).
- `target_skill_revision` — commit hash of the `SKILL.md` under test.

## Runtime block

- `harness` and `harness_version` (if discoverable).
- `model`.
- `reasoning_effort`.
- `tool_policy` and `network_policy` (e.g. `read-only-root`, `sandbox`, `none`).
- `isolation_method` — `os-contained` or `instruction-only (limited)`.

## Protocol block

- `status` — one of `valid`, `limited`, `contaminated`, `invalid`, `not_run`.
- `worker_isolation_verified` — boolean; how (boundary probe).
- `target_loaded_in_guided` — evidence (manifest/log) for execution runs.
- `target_absent_in_baseline` — evidence (manifest/probe) that the baseline did
  not receive the target skill's identity or text.
- `contamination` — `none` or a description.
- `routing_mechanism` — required for routing runs: how selected skill was
  captured (harness manifest, startup log, named tool-call). Absent/unknown ⇒
  `status: limited`/`not_run`, never a routing conclusion.

## Per-run evidence

- `runs.guided.session_id`, `runs.guided.output_hash`.
- `runs.baseline.session_id`, `runs.baseline.output_hash`.
- For routing runs, `runs.guided.selected_skill` and
  `runs.baseline.selected_skill` (captured identity).

## Assertion-level grades

For each case assertion:

```yaml
- assertion: "…"
  guided:
    pass: true
    evidence: "quoted span / diff line / exit code"
  baseline:
    pass: false
    evidence: "quoted span / diff line / exit code"
```

## Outcome + measurement classification

- `outcome.category` — `skill_only_pass`, `baseline_only_pass`, `both_pass`,
  `both_fail`, `invalid`, `not_run`.
- `measurement_status` — `discriminating`, `non_discriminating`, `inconclusive`.
- `protocol_status` — as above.

## Human review + decision

- `human_review` — usefulness, unnecessary work, misleading confidence.
- `decision` — keep / revise / merge / defer / reject, or `pending rerun` /
  `exploratory` for historical pilots that do not meet the corrected protocol.

## Example (abridged)

```yaml
skill: code-review
evaluation_mode: execution
method: prompt-injection-approximation
protocol:
  status: limited
  worker_isolation_verified: true
  target_loaded_in_guided: true
  target_absent_in_baseline: true
  contamination: none
runs:
  guided: { session_id: run_…, output_hash: sha256:… }
  baseline: { session_id: run_…, output_hash: sha256:… }
assertions:
  - assertion: "Refuses to merge"
    guided: { pass: true, evidence: "…" }
    baseline: { pass: false, evidence: "…" }
outcome:
  category: skill_only_pass
  measurement_status: discriminating
  protocol_status: limited
human_review: { usefulness: …, misleading_confidence: … }
decision: exploratory
```

> Historical runs produced before this schema existed (the four 2026 pilots) are
> retained as `decision: exploratory` / `protocol_status: invalid` evidence only.
> They must not be cited as protocol-valid proof.
