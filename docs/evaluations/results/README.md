# Evaluation results — storage and validation

This directory tracks **executed** evaluation runs so the validation matrix can be kept over time. A result is only valid when the two conditions were run by genuinely independent workers or harness sessions; a single agent instructed to answer "as if" it had not seen the skill is not an evaluation.

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
  "model": {"provider": "meta", "name": "muse-spark-1.2-contributor", "reasoning_effort": "xhigh"},
  "baseline": "harness-default",
  "protocol_status": "valid",
  "skills": [
    {
      "skill_name": "bootstrap-project",
      "skill_commit": "c4c79e1",
      "evaluation_sha256": "<hash of the frozen eval definition>",
      "case_manifest": [
        {"id": 1, "kind": "matching", "assertions_total": 4},
        {"id": 2, "kind": "neighboring", "assertions_total": 2}
      ],
      "cases": [
        {"id": 1, "kind": "matching", "assertions_total": 4, "skill_pass": 4, "baseline_pass": 0, "better": true},
        {"id": 2, "kind": "neighboring", "assertions_total": 2, "skill_pass": 2, "baseline_pass": 0, "better": true}
      ],
      "overall_better": true,
      "measurement_status": "discriminating",
      "decision": "KEEP"
    }
  ]
}
```

**Rules enforced by `scripts/validate_repository.py`:**

* `schema_version == 1`, `run_id` non-empty, `timestamp` ISO-8601.
* `harness.name`/`model.name` non-empty; `baseline` is `harness-default`,
  `no-skill`, or a previous-version label. Use `harness-default` when the
  normal harness is present and only the target skill is omitted.
* `skills[]` non-empty; each `skill_name` must match an existing skill directory and its committed `evals/evals.json`.
* Each `cases[]` entry: `id` matches the committed eval case `id`, `kind` matches, `assertions_total == skill_pass + failures` and equals the committed `assertions` length, `skill_pass`/`baseline_pass` in `[0, assertions_total]`, `better == (skill_pass > baseline_pass)` when `overall_better` is claimed only if at least one meaningful `better=true`.
* `decision` in `KEEP`, `KEEP_PROVISIONAL`, `REVISE`, `MERGE`, `DEFER`, `REJECT`, or `INCONCLUSIVE`.
* New results should include `protocol_status: "valid"` and each skill entry
  should include `measurement_status: "discriminating"`,
  `"non_discriminating"`, or `"inconclusive"`. A valid protocol with a tied
  or ceiling-effect result is `measurement_status: "inconclusive"` (or
  `"non_discriminating"`) and must not be interpreted as evidence that the
  skill is ineffective. `INCONCLUSIVE` is the appropriate decision until a
  stronger case set is run. Older results may omit these fields and remain
  historical evidence only.
* `skill_commit` records the core `SKILL.md` revision being evaluated; the exact `evals/evals.json` and `evals/files/` snapshot evaluated is the one captured in this result (see `timestamp`/`run_id` and the committed files at that time).
* When a result is retained after its committed eval definition changes, include
  `evaluation_sha256` and a `case_manifest` with each frozen case's `id`, `kind`,
  and `assertions_total`. The validator uses that manifest to preserve the
  historical comparison instead of silently grading it against a new case set.
* Linked file must exist when referenced from `validation-matrix.md`.

## Cost-aware execution

A complete five-case pack requires ten fresh workers per repetition. When the
goal is to validate the protocol or screen a benchmark, use one fixed,
lower-cost model/effort for the whole pack and record that exact setting. Use a
stronger or more expensive model for a separate confirmation run when needed;
never combine scores across model or effort settings. After each worker has an
OS-contained root and parent-only trace directory, case pairs may run in
parallel to reduce wall-clock time. Stop and discard any interrupted or
model-switched partial run rather than treating it as a full result.

## Non-negotiable independent-worker protocol

The baseline condition must be real, not role-played. For every case and every
repetition, the runner must launch two different fresh subagents or harness
sessions:

* `WITH-SKILL`: a clean worker whose harness actually loads the target
  `SKILL.md` revision;
* `BASELINE`: a separate clean worker initialized without that skill, its
  references, generated projections, prior result files, or the other worker's
  transcript.

It is unacceptable to run both conditions in one conversation, ask a worker to
ignore/forget/pretend it did not see the skill, or infer skill absence from a
worker's self-report. The prompt, fixtures, tools, network policy, model,
reasoning effort, and output contract should be equivalent; only the intended
guidance condition may differ. Use separate per-condition workspaces copied
from the same fixture snapshot, not two subdirectories visible to one worker.
The runner must set the worker's actual working directory to the neutral
fixture root or verify `pwd` and an immediate file manifest before the task
begins; mentioning a path in the prompt is not isolation. If a worker starts in
the catalog repository or can see sibling evaluation metadata, discard the run.
Keep the workers blind to the evaluation: give them the natural task prompt,
not an evaluation wrapper, and do not tell them they are workers, name the
case, mention `WITH-SKILL`/`BASELINE`, disclose that a comparison is happening,
or reveal the expected behavior. If the harness itself exposes an injection
label, target skill name/path/description, catalog entry, or other target-skill
identity in system context, record that limitation and do not call the run fully
blinded. A baseline must not learn the target skill's identity merely because
the harness automatically projects the skill catalog or tool manifest; discard
the condition if it does. Use
neutral worker-visible workspace and file names; do not encode the skill name,
condition, case ID, or evaluation purpose in paths or filenames.

The run evidence must preserve, outside the committed summary, the worker or
session identifiers, the loaded-guidance manifest (or equivalent harness
evidence), the target skill revision for `WITH-SKILL`, and an explicit
target-skill-absent check for `BASELINE`. Grade with a deterministic checker,
human reviewer, or a third fresh grader that shares neither worker transcript;
workers must not grade themselves. If the harness cannot create and verify this
separation, do not record a result as an executed comparison and leave the
matrix cell untested. Any context, workspace, memory, skill-cache, or prompt
contamination invalidates both conditions; discard them and rerun with new
workers rather than repairing the prompt or scoring around the contamination.

Filesystem containment is part of this boundary. A random neutral directory
name is insufficient if the worker can climb to a shared temporary parent and
enumerate sibling evaluation roots, catalog checkouts, other worktrees,
memory, or parent-only logs. Use an OS-level jail, container, or equivalent
profile that permits the worker root and required harness runtime files while
denying those unrelated paths. Preserve parent-side probes showing that the
worker root is readable, parent traversal is denied or contains no other
evaluation material, and the catalog/skill cache is unavailable. A run that
passes the prompt/fixture checks but fails this filesystem boundary is
contaminated and must not be scored.

Workers must receive only the actual case prompt, declared fixtures, and the
guidance available in their condition. Do not pass them `expected_output`,
assertions, scoring rubrics, the other condition's output, suspected findings,
or instructions to grade/evaluate their own response. The parent grades the
frozen assertions against both outputs, or uses a separate fresh grader that
receives neither worker transcript nor target-skill guidance. If a worker saw
evaluation criteria beyond the task contract, discard that condition and rerun
it from a fresh context.

### Codex CLI isolation recipe

For a Codex CLI runner, launch each worker with a real neutral root using
`codex exec --cd <neutral-root> --ephemeral --ignore-user-config
--ignore-rules` plus a sandbox appropriate to the task. Report-only tasks may
use an isolated write-enabled root so the parent can inspect the final diff;
read-only is appropriate only when the task truly cannot require writes. Keep
raw stdout, stderr, and JSONL session traces in a parent-only temporary
directory outside the worker root. Never redirect those artifacts into the
workspace: a worker can inspect its own trace, which violates the declared-file
boundary even if no target-skill text appears in it.

On macOS, the inner Codex sandbox may block a nonstandard contained root. After
verifying an outer `sandbox-exec`/seatbelt profile that denies shared temp,
catalog/worktree, memory, and parent-log paths and allows only the worker root,
the runner may use `--dangerously-bypass-approvals-and-sandbox` so the outer
profile remains authoritative. This flag is invalid without that outer
containment, and the run record must state its use and the denied-path probes.

Use two neutral `AGENTS.md` variants. Both should require the same `pwd` and
local-file preflight. The guided variant may explicitly read a neutral path
such as `.agents/skills/task-quality/SKILL.md`; the baseline variant must not
mention that path, missing guidance, or the fact that another condition has
extra instructions. The guided root contains the target skill at that neutral
path; the baseline root contains no `.agents` guidance tree. Do not use an
`if-exists` instruction in the baseline: it leaks the condition.

## Human-readable companion

Every `*.json` has a `*.md` sibling with the same basename — e.g., `2026-08-11-muse-spark-1.2-contributor-muse-code.md` — containing the summary table, per-skill `skill_pass`/`baseline_pass`/`better`, and decision. Keep them in sync; the markdown is for humans, the JSON is for validation. The matrix links to both (`json` · `human`).

## How to add a run

The human interface is conversation only — ask the agent to “run evals” or “record an eval run”; the agent executes all steps below and the human does not need to run scripts manually.

1. Agent determines `harness` (`muse code` + version), `model` (`muse-spark-1.2-contributor` + provider), and `reasoning_effort` (`xhigh` currently used; can dramatically change results). Use runtime metadata when available. **If the agent cannot definitively determine the harness, model, or effort level, it asks the user explicitly** (e.g., “Which harness/model/effort should I record for this run? Currently using `muse code` / `muse-spark-1.2-contributor` / `xhigh` — confirm or provide the correct values”) and does not guess. Then the agent creates separate per-condition workspaces from the same fixture snapshot and launches a fresh `WITH-SKILL` subagent/session and a different fresh `BASELINE` subagent/session for each case and repetition. Give both only the natural task prompt and allowed fixtures; do not tell them they are being evaluated or reveal the case, baseline, expected output, assertions, or rubric. The baseline must be genuinely skill-free; telling the same agent to ignore the skill is prohibited.
2. Agent verifies the independent worker/session boundary, then grades every `assertions` entry itself with quoted evidence from both outputs; raw outputs and boundary evidence stay in the ephemeral workspace (not here). Workers do not receive the assertions or grade themselves. If the boundary cannot be verified, or if the workers saw the scoring criteria, the run is invalid and must not receive a matrix mark.
3. Agent writes the JSON above **and** its `*.md` human-readable companion (copy the shape from `2026-08-11-muse-spark-1.2-contributor-muse-code.md`).
4. Agent updates `docs/evaluations/validation-matrix.md` to link both `json` and `human` files.
5. Agent regenerates the aggregate with `python3 scripts/generate_evaluation_summary.py --write` — this keeps [`docs/evaluations/SUMMARY.md`](../SUMMARY.md) (latest per skill × harness × model) in sync.
6. Agent runs `make check` — the validator checks the JSON, the matrix links, and that `SUMMARY.md` is fresh.

## Current harness/model identifiers

* Harness: `muse code` (this repository's active coding harness; version from `muse --version` or `0.1.0` if not exposed).
* Model: `muse-spark-1.2-contributor` (`provider: meta`). Record `reasoning_effort` when the harness exposes it (e.g., `low`).

Do not claim `better` or `KEEP` without evidence-graded assertions. One run per condition per model is smoke-level evidence — repeat across models/harnesses before portability claims.
