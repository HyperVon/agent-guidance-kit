# Evaluation result schema

Committed result files live under `docs/evaluations/results/<skill>.md`. They are
sanitized summaries: keep enough quoted evidence to justify every assertion
decision, but store raw worker outputs, session logs, and tool trajectories in
the ignored local run-evidence directory (see `.gitignore`), not in Git.

A result file MUST contain, in addition to any prose, a fenced
`result-json` block that the validator (`scripts/validate_evaluations.py`)
parses and checks. The block is JSON.

## Execution result (Layer B, Docker-isolated)

```result-json
{
  "skill": "code-review",
  "evaluation_mode": "execution",
  "method": "docker-isolated",
  "case_revision": "sha256:…",
  "fixture_revision": "sha256:…",
  "target_skill_revision": "sha256:…",
  "runtime": {
    "harness": "kilo",
    "harness_version": "1.1.17",
    "model": "kilo/tencent/hy3:free",
    "reasoning_effort": "high",
    "tool_policy": "sandbox",
    "network_policy": "none",
    "isolation_method": "docker"
  },
  "protocol": {
    "status": "valid",
    "tier": "tier-2-strict-isolated",
    "worker_isolation_verified": true,
    "target_guidance_present": "boundary probe confirmed /work/guidance/task/SKILL.md present",
    "target_guidance_hash": "sha256:…",
    "target_absent_in_baseline": "boundary probe confirmed /work/guidance/task/SKILL.md absent",
    "baseline_guidance_absent": "boundary probe confirmed no guidance tree in baseline",
    "contamination": "none",
    "natural_task_identical_across_conditions": true,
    "natural_task_hash": "sha256:…",
    "routing_mechanism": null,
    "conditions": ["target", "baseline", "placebo"],
    "target_skill_kilo_path": ".kilo/skills/code-review",
    "placebo_skill_kilo_path": ".kilo/skills/security-review",
    "target_skill_loaded": true,
    "placebo_skill_loaded": true,
    "skill_loads": [
      {"path": ".kilo/skills/code-review/SKILL.md", "timestamp": "…"}
    ]
  },
  "runs": {
    "target":   { "session_id": "t1", "container_id": "ct1" },
    "baseline": { "session_id": "b1", "container_id": "cb1" },
    "placebo":  { "session_id": "p1", "container_id": "cp1" }
  },
  "cases": [
    {
      "case_id": 1,
      "outcome": {
        "category": "skill_only_pass",
        "measurement_status": "discriminating",
        "protocol_status": "valid"
      },
      "verdict": { "target_pass": true, "baseline_pass": false, "placebo_pass": false },
      "assertions": [
        {
          "assertion": "<frozen assertion text, verbatim from evals.json>",
          "target":   { "pass": true,  "evidence": "quoted span / diff line / exit code" },
          "baseline": { "pass": false, "evidence": "quoted span / diff line / exit code" },
          "placebo":  { "pass": false, "evidence": "quoted span / diff line / exit code" }
        }
      ]
    }
  ]
}
```

## Routing result

For `evaluation_mode: "routing"` the `result-json` block grades **harness
selection evidence** (Layer C), not worker output. It records the skill the
harness selected in each condition and lets the validator check it against the
case's `routing` expectation. No execution `assertions` are graded.

```result-json
{
  "skill": "code-review",
  "evaluation_mode": "routing",
  "method": "harness-routing",
  "case_revision": "sha256:…",
  "fixture_revision": "sha256:…",
  "target_skill_revision": "sha256:…",
  "runtime": {
    "harness": "kilo",
    "harness_version": "1.1.17",
    "model": "kilo/tencent/hy3:free",
    "reasoning_effort": "high",
    "tool_policy": "sandbox",
    "network_policy": "none",
    "isolation_method": "instruction-only (limited)"
  },
  "protocol": {
    "status": "limited",
    "worker_isolation_verified": true,
    "target_guidance_present": null,
    "target_absent_in_baseline": null,
    "contamination": "none",
    "routing_mechanism": "harness startup log names selected skill"
  },
  "runs": {
    "target":   { "session_id": "t1", "selected_skill": "code-review" },
    "baseline": { "session_id": "b1", "selected_skill": null }
  },
  "cases": [
    {
      "case_id": 1,
      "outcome": {
        "category": "both_pass",
        "measurement_status": "discriminating",
        "protocol_status": "limited"
      },
      "verdict": { "target_pass": true, "baseline_pass": true },
      "runs": {
        "target":   { "selected_skill": "code-review" },
        "baseline": { "selected_skill": null }
      }
    }
  ]
}
```

  - `runs.target.selected_skill` — the skill the harness selected in the
    target-present condition (must be present in the dict; null is only valid when
    the expectation allows it via `allowed_fallbacks`).
  - `runs.baseline.selected_skill` — the skill selected in the target-absent
    condition; `null` means the harness declined to select the (absent) target,
    which is the expected baseline outcome.
  - The validator compares each captured selection to the case's
    `routing.target_present` / `routing.target_absent` expectation and fails the
    case when the `verdict` booleans disagree with the captured selection.

## Docker execution evidence (Layer B, local)

For `evaluation_mode: "execution"` the worker runs in **fresh Docker containers**
(see `isolation-protocol.md` and `Dockerfile.eval`), so the run can be
`protocol.status: valid` with genuine OS-level isolation. The raw runner evidence
(`scripts/run_execution_eval.py`) is written to `.eval-evidence/exec-<skill>-case<id>.json`
(gitignored) with top-level `"evidence_type": "execution"` and **one repetition
per independent seed copy**.

Each repetition MUST prove:

- **Independent starting state.** The runner derives one pristine seed, then
  makes one independent copy per condition and records `starting_fixture_hash`
  for each. The validator requires all `starting_fixture_hash` values to equal
  `canonical_seed_hash`. The condition workers therefore begin from
  byte-identical state and can never share a mutable fixture.
- **Distinct execution.** `conditions.target.container_id` ≠
  `conditions.baseline.container_id` (and ≠ `conditions.placebo.container_id`
  when a placebo is present), and likewise for `session_id`. This is verified
  per-repetition via `distinct_containers` / `distinct_sessions`.
- **Guidance boundary (probed inside the container).**
  `conditions.target.guidance_verified` is `true` only if an in-container probe
  found the mounted skill guidance at `/work/guidance/task/SKILL.md`;
  `conditions.baseline.guidance_verified_absent` is `true` only if the probe
  confirmed its *absence* (baseline has no guidance mounted and the probe must
  return `absent`). A bare text claim is not accepted — `guidance_probe` must be
  `present`/`absent`/missing as verified inside the container.
- **Failure is not evidence.** If the Docker/Kilo invocation returned non-zero, the
  container never started, the model output was empty/unparseable, or no session id
  was produced, the condition's `run_status="failed"` and the validator
  **rejects** the file. `returncode` must be `0` for all conditions.
- **Task-state mutation recorded.** `conditions.<name>.ending_fixture_hash`
  proves what each worker changed relative to `starting_fixture_hash`
  (they must differ for productive conditions). Optional filesystem snapshots
  (`conditions.<name>.filesystem_snapshot_before/after`) capture the concrete
  diff. The `natural_task_identical_across_conditions` flag confirms the task
  text was byte-identical across conditions.

The validator dispatches on `evidence_type` and checks the file with
`python3 scripts/validate_evaluations.py --check-evidence`; unknown/malformed
evidence is a hard error, never silently skipped.

## Required identity

- `skill` — must match a discovered `evals.json` `skill_name`.
- `evaluation_mode` — `execution` (Layer B, Docker-isolated) or `routing`
  (harness selection). Catalog-discriminability (Layer A) evidence is stored as
  `evidence_type: "catalog-routing"` in the local evidence dir, not in committed
  result files; it produces confusion-set confusion matrices, not per-case
  routing verdicts.
- `method` — `docker-isolated` (execution, Tier 2) or `harness-routing`
  (Layer C, routing). `prompt-injection-approximation` is historical/`invalid`.
- `case_revision` — commit/content hash of the `evals.json` used.
- `fixture_revision` — commit/content hash of the fixture (`designed_only` if none).
- `target_skill_revision` — commit hash of the `SKILL.md` under test.

## Runtime block

`harness`, `model`, `reasoning_effort`, `tool_policy`, `network_policy`,
`isolation_method` are all required. `harness_version` is allowed to be
`"unknown"` when not discoverable. `isolation_method` should be `docker` (OS-level)
for a `valid` execution run; `instruction-only (limited)` is only valid for
Tier 1 fast-developer mode with `protocol_status: limited`.

## Protocol block

- `status` — `valid`, `limited`, `contaminated`, `invalid`, `not_run`.
- `tier` — `tier-1-fast-dev`, `tier-2-strict-isolated`, or `tier-3-harness-native`.
- `worker_isolation_verified` — boolean; how (boundary probe). A `valid` run
  requires it `true`.
- `target_guidance_present` — evidence (manifest/log/probe) that the target
  worker's guidance was loaded at the neutral path. **Required for execution
  runs**; must be `null` for routing runs.
- `target_guidance_hash` — the frozen hash of the guidance bundle the target
  condition received. **Required for execution runs.**
- `target_absent_in_baseline` — evidence that the baseline did **not** receive
  the target skill's identity or text. **Required for execution runs.**
- `baseline_guidance_absent` — evidence the baseline mounted no guidance tree.
- `contamination` — `none` or a description.
- `natural_task_identical_across_conditions` — `true` only when the runner
  verified the worker-visible prompt hash is identical across all conditions.
- `natural_task_hash` — the frozen task hash.
- `routing_mechanism` — **required for routing runs**: how the selected skill
  was captured (harness manifest, startup log, named tool-call). Absent/unknown
  ⇒ the routing claim is invalid, never a routing conclusion.
- `conditions` — list of condition names used (`target`/`baseline`/`placebo`).

## Per-case grades

- `outcome.category` — `skill_only_pass`, `baseline_only_pass`, `both_pass`,
  `both_fail`, `non_discriminating`, `invalid`, `not_run`.
- `outcome.measurement_status` — `discriminating`, `non_discriminating`,
  `inconclusive`.
- `outcome.protocol_status` — as above.
- `verdict.target_pass` / `verdict.baseline_pass` / `verdict.placebo_pass` —
  booleans; the validator checks they are consistent with `outcome.category`:
  - `skill_only_pass` ⇔ target passes, baseline fails, placebo fails
  - `baseline_only_pass` ⇔ target fails, baseline passes
  - `both_pass` ⇔ target and baseline both pass
  - `both_fail` ⇔ target, baseline, and placebo all fail
  - `non_discriminating` ⇔ all conditions pass equally (no skill advantage)
- **Execution mode** — every frozen assertion from `evals.json` must appear in
  the graded `assertions` list (no assertion silently disappears). Each assertion
  grades `target` and `baseline` (and `placebo` when present) with a `pass`
  boolean; **every passing condition must carry concrete `evidence`** (quoted
  span / diff line / exit code) — plausible prose or self-assertion is not
  evidence.
- **Routing mode** — no execution `assertions` are graded. Instead each case's
  `runs.target.selected_skill` / `runs.baseline.selected_skill` are checked
  against the case `routing` expectation (`target_present.expected_selected_skill`
  and `target_absent.expected_selected_skill`, with `allowed_fallbacks`). A
  routing result may not claim a passing `verdict` on a condition whose captured
  selection does not satisfy the expectation.

## Protocol-validity gates

A result MUST NOT be treated as validated when:

- `protocol.status` is `invalid` or `contaminated`;
- required worker-isolation evidence is missing;
- target guidance is unverified (execution);
- target absence is unverified (execution);
- the routing selection identity is unavailable (routing);
- `natural_task_identical_across_conditions` is not `true` (execution);
- conditions share a container or session id (execution).

Concretely: when `protocol.status` is `invalid` or `contaminated`, no case may
claim a success outcome (`skill_only_pass` / `baseline_only_pass` / `both_pass`).

## Historical pilots

The four 2026 pilots (`code-review.md`, `git-github-workflow.md`,
`review-feedback-resolution.md`, `security-review.md`) predate this schema.
They are retained only as `protocol_status: invalid` / `decision: exploratory`
legacy evidence and are exempt from the `result-json` requirement. The
validator allows them **only** when they are explicitly marked exploratory/invalid
and carry no overloaded `✓` or `authoritative` claim.
