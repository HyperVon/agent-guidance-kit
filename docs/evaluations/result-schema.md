# Evaluation result schema

Committed result files live under `docs/evaluations/results/<skill>.md`. They are
sanitized summaries: keep enough quoted evidence to justify every assertion
decision, but store raw worker outputs, session logs, and tool trajectories in
the ignored local run-evidence directory (see `.gitignore`), not in Git.

A result file MUST contain, in addition to any prose, a fenced
`result-json` block that the validator (`scripts/validate_evaluations.py`)
parses and checks. The block is JSON:

```result-json
{
  "skill": "code-review",
  "evaluation_mode": "execution",
  "method": "prompt-injection-approximation",
  "case_revision": "sha256:…",
  "fixture_revision": "sha256:…",
  "target_skill_revision": "sha256:…",
  "runtime": {
    "harness": "kilo",
    "harness_version": "unknown",
    "model": "hy3-free",
    "reasoning_effort": "high",
    "tool_policy": "sandbox",
    "network_policy": "none",
    "isolation_method": "instruction-only (limited)"
  },
  "protocol": {
    "status": "limited",
    "worker_isolation_verified": true,
    "target_loaded_in_guided": "manifest shows code-review/SKILL.md loaded",
    "target_absent_in_baseline": "baseline manifest contained no code-review entry",
    "contamination": "none",
    "routing_mechanism": null
  },
  "cases": [
    {
      "case_id": 1,
      "outcome": {
        "category": "skill_only_pass",
        "measurement_status": "discriminating",
        "protocol_status": "limited"
      },
      "verdict": { "guided_pass": true, "baseline_pass": false },
      "assertions": [
        {
          "assertion": "<frozen assertion text, verbatim from evals.json>",
          "guided":   { "pass": true,  "evidence": "quoted span / diff line / exit code" },
          "baseline": { "pass": false, "evidence": "quoted span / diff line / exit code" }
        }
      ]
    }
   ]
 }
 ```

### Routing result

For `evaluation_mode: "routing"` the `result-json` block grades **harness
selection evidence**, not worker output. It records the skill the harness
selected in each condition and lets the validator check it against the case's
`routing` expectation. No execution `assertions` are graded.

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
    "harness_version": "unknown",
    "model": "hy3-free",
    "reasoning_effort": "high",
    "tool_policy": "sandbox",
    "network_policy": "none",
    "isolation_method": "instruction-only (limited)"
  },
  "protocol": {
    "status": "limited",
    "worker_isolation_verified": true,
    "target_loaded_in_guided": null,
    "target_absent_in_baseline": null,
    "contamination": "none",
    "routing_mechanism": "harness startup log names selected skill"
  },
  "runs": {
    "guided":   { "session_id": "g1", "output_hash": "sha256:…" },
    "baseline": { "session_id": "b1", "output_hash": "sha256:…" }
  },
  "cases": [
    {
      "case_id": 1,
      "outcome": {
        "category": "both_pass",
        "measurement_status": "discriminating",
        "protocol_status": "limited"
      },
      "verdict": { "guided_pass": true, "baseline_pass": true },
      "runs": {
        "guided":   { "selected_skill": "code-review" },
        "baseline": { "selected_skill": null }
      }
    }
  ]
}
```

- `runs.guided.selected_skill` — the skill the harness selected in the
  target-present condition (must be present; null is only valid when the
  expectation allows it via `allowed_fallbacks`).
- `runs.baseline.selected_skill` — the skill selected in the target-absent
  condition; `null` means the harness declined to select the (absent) target,
  which is the expected baseline outcome.
- The validator compares each captured selection to the case's
  `routing.target_present` / `routing.target_absent` expectation and fails the
  case when the `verdict` booleans disagree with the captured selection.

## Required identity

- `skill` — must match a discovered `evals.json` `skill_name`.
- `evaluation_mode` — `routing` or `execution`.
- `method` — `harness-routing`, `harness-injection`, or
  `prompt-injection-approximation`.
- `case_revision` — commit/content hash of the `evals.json` used.
- `fixture_revision` — commit/content hash of the fixture (`designed_only` if none).
- `target_skill_revision` — commit hash of the `SKILL.md` under test.

## Runtime block

`harness`, `model`, `reasoning_effort`, `tool_policy`, `network_policy`,
`isolation_method` are all required. `harness_version` is allowed to be
`"unknown"` when not discoverable.

## Protocol block

- `status` — `valid`, `limited`, `contaminated`, `invalid`, `not_run`.
- `worker_isolation_verified` — boolean; how (boundary probe). A `valid` run
  requires it `true`.
- `target_loaded_in_guided` — evidence (manifest/log) that the guided worker
  loaded the target skill. **Required for execution runs.**
- `target_absent_in_baseline` — evidence that the baseline did **not** receive
  the target skill's identity or text. **Required for execution runs**; if it is
  missing or false the run is unverified and invalid.
- `contamination` — `none` or a description.
- `routing_mechanism` — **required for routing runs**: how the selected skill
  was captured (harness manifest, startup log, named tool-call). Absent/unknown
  ⇒ the routing claim is invalid, never a routing conclusion.

## Per-case grades

- `outcome.category` — `skill_only_pass`, `baseline_only_pass`, `both_pass`,
  `both_fail`, `invalid`, `not_run`.
- `outcome.measurement_status` — `discriminating`, `non_discriminating`,
  `inconclusive`.
- `outcome.protocol_status` — as above.
- `verdict.guided_pass` / `verdict.baseline_pass` — booleans; the validator
  checks they are consistent with `outcome.category`:
  - `skill_only_pass` ⇔ guided pass & baseline fail
  - `baseline_only_pass` ⇔ guided fail & baseline pass
  - `both_pass` ⇔ both pass
  - `both_fail` ⇔ both fail
- **Execution mode** — every frozen assertion from `evals.json` must appear in
  the graded `assertions` list (no assertion silently disappears). Each
  assertion grades `guided` and `baseline` with a `pass` boolean; **every
  passing condition must carry concrete `evidence`** (quoted span / diff line /
  exit code) — plausible prose or self-assertion is not evidence.
- **Routing mode** — no execution `assertions` are graded. Instead each case's
  `runs.guided.selected_skill` / `runs.baseline.selected_skill` are checked
  against the case `routing` expectation (`target_present.expected_selected_skill`
  and `target_absent.expected_selected_skill`, with `allowed_fallbacks`). A
  routing result may not claim a passing `verdict` on a condition whose captured
  selection does not satisfy the expectation.

## Protocol-validity gates

A result MUST NOT be treated as validated when:

- `protocol.status` is `invalid` or `contaminated`;
- required worker-isolation evidence is missing;
- target absence is unverified (execution);
- the routing selection identity is unavailable (routing).

Concretely: when `protocol.status` is `invalid` or `contaminated`, no case may
claim a success outcome (`skill_only_pass` / `baseline_only_pass` /
`both_pass`).

## Historical pilots

The four 2026 pilots (`code-review.md`, `git-github-workflow.md`,
`review-feedback-resolution.md`, `security-review.md`) predate this schema.
They are retained only as `protocol_status: invalid` / `decision: exploratory`
legacy evidence and are exempt from the `result-json` requirement. The
validator allows them **only** when they are explicitly marked exploratory/invalid
and carry no overloaded `✓` or `authoritative` claim.
