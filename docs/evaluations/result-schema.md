# Evaluation result schema

New harness-neutral records follow the [canonical protocol specification](protocol-spec.md).

Committed result files live under `docs/evaluations/results/<skill>.md`. They are
sanitized summaries: keep enough quoted evidence to justify every assertion
decision, but store raw worker outputs, session logs, and tool trajectories in
the ignored local run-evidence directory (see `.gitignore`), not in Git.

A result file MUST contain, in addition to any prose, a fenced
`result-json` block that the validator (`scripts/validate_evaluations.py`)
parses and checks. The block is JSON.

## Protocol declarations

New results declare the protocol that answers the evaluation question. The
validator takes condition and repetition requirements from this declaration;
it does not assume one universal target/baseline/placebo experiment.

| Protocol | Required conditions | Minimum repetitions | Question |
| --- | --- | ---: | --- |
| `smoke` | `target` | 1 | Does the orchestration and activation path work? |
| `qualification` | `target`, `baseline` | 1 | Does the skill add fair common-denominator value? |
| `regression` | `candidate`, `reference` | 1 | Did a skill revision improve, preserve, or regress behavior? |
| `confirmation` | `target`, `baseline`, `placebo` | 3 | Does strict repeated isolated evidence support an important efficacy claim? |

## Harness-neutral comparison result

The core result schema does not require a particular agent CLI, model
provider, container runtime, or discovery directory. Use `method:
"harness-adapter"` and record the adapter name/version in optional runtime or
adapter metadata. New records separate `result_schema_version`,
`evidence_protocol_version`, and `adapter_protocol_version`. See [the adapter
contract](harness-adapter.md) for the request/response boundary.

Raw neutral evidence records evaluator-owned workspace receipts and, for every
guided condition, the canonical guidance identity (`guidance_identity`,
`guidance_hash`, `activation_method`, `activation_evidence`) plus
`activation_verified` and `context_verified`. The receipt is read from a random
file inside the requested
workspace and checked against the evaluator's expected hash, so distinct
worker/session IDs alone cannot prove workspace isolation. The validator checks
what guidance identity was active; it does not require a Kilo path, filesystem
placement, CLI name, or one universal activation mechanism. The former
`guidance_id`, `guidance_source`, `guidance_probe`, and
`activation_mechanism` names remain compatibility aliases.

Each new neutral condition may also carry `attestation_layers`. This makes the
trust chain explicit: `adapter_claims` is what the adapter says,
`evaluator_verification` is what the validator recomputes for consistency, and
`independent_attestation` records an optional external/runtime source. An
adapter claim is never relabeled as independent proof. Legacy evidence may
omit the object and remains readable at its original confidence level.

Neutral regression evidence is revision-anchored. Its
`case_anchors.candidate` and `case_anchors.reference` entries bind each
revision's `evals/evals.json` hash, prompt hash, fixture declaration, frozen
fixture hash, and (for generators) generator-source hash. `fixture_revision`
identifies the reference revision that supplied the shared worker-visible task.
The candidate declaration is recorded for provenance, but its fixture and
generator are not materialized or executed; the evaluator uses the reference
fixture for both conditions. Validation resolves both anchors from their
recorded Git revisions, so a historical candidate is not reinterpreted using
the current checkout's evals or fixtures.

Regression evidence schema version 3 additionally records immutable
`candidate_skill_hash`, `reference_skill_hash`, `case_set_hash`, `fixture_hash`,
`runner_version`, and `reproduction_status`. The case-set hash covers both
revision-local anchors; the fixture hash identifies the exact shared task; and
the runner version identifies the metadata/validation contract. If either Git
revision, case anchor, or fixture cannot be resolved exactly, validation returns
`INVALID_REPRODUCTION_ENVIRONMENT` and the evidence cannot be a pass. Version 2
artifacts remain readable through the compatibility path.

The comparison lifecycle is intentionally separate:

| Stage | Canonical fields | Meaning |
| --- | --- | --- |
| Activation | `activation_verified`, `context_verified` | Guidance identity/context was observed for the condition. |
| Execution attestation | `execution_attestation`, `execution_verified` | Returned execution facts are bound; `execution_verified` additionally requires strong confidence. |
| Isolation | `isolation_attestation`, `worker_isolation_verified` | The worker boundary was independently attested. |
| Protocol result | `protocol.status` | Aggregate protocol validity after the preceding gates. |

`execution_verified` is not a synonym for `protocol.status: valid`, and an
activation probe is not an isolation proof.

For a `valid` execution or regression comparison, `protocol.isolation_attestation`
is also required. It must use the
`agent-guidance-kit.isolation-attestation/v1` protocol, report
`status: "verified"`, `verification_mode: "independent"`, and
`boundary: "os-level"`,
match `runtime.isolation_method`, and map every case ID to that case's
`raw_evidence_hash`. Valid comparisons must provide a SHA-256
`raw_evidence_hash` for every case. The validator checks these structural and
hash bindings; the adapter remains the trust boundary for provider-specific
worker and isolation facts, so a result must not claim independent OS evidence
that its adapter did not actually obtain.

The following is a compact regression result shape. A qualification result uses
`target`/`baseline` conditions; a smoke may use only `target`.

```result-json
{
  "result_schema_version": 3,
  "evidence_protocol_version": 3,
  "adapter_protocol_version": "agent-guidance-kit.harness-adapter/v1",
  "skill": "code-review",
  "evaluation_mode": "regression",
  "method": "harness-adapter",
  "case_revision": "sha256:…",
  "fixture_revision": "sha256:…",
  "candidate_skill_revision": "git:…",
  "reference_skill_revision": "git:…",
  "candidate_skill_hash": "sha256:…",
  "reference_skill_hash": "sha256:…",
  "case_set_hash": "sha256:…",
  "fixture_hash": "sha256:…",
  "runner_version": "agent-guidance-kit.regression-runner/v2",
  "reproduction_status": "reproducible",
  "runtime": {
    "harness": "adapter-name",
    "harness_version": "adapter-defined",
    "model": "provider/model-or-runtime-id",
    "reasoning_effort": "adapter-defined",
    "tool_policy": "adapter-defined",
    "network_policy": "adapter-defined",
    "isolation_method": "sandbox"
  },
  "protocol": {
    "name": "regression",
    "status": "limited",
    "tier": "tier-1-fast-dev",
    "worker_isolation_verified": true,
    "execution_verified": false,
    "attestation_confidence": "adapter_declared",
    "isolation_attestation": {
      "protocol": "agent-guidance-kit.isolation-attestation/v1",
      "status": "verified",
      "verification_mode": "independent",
      "boundary": "os-level",
      "worker_isolation_verified": true,
      "isolation_method": "sandbox",
      "evidence_hashes": {"5": "sha256:…"}
    },
    "conditions": ["candidate", "reference"],
    "repeats": 1
  },
  "cases": [
    {
      "case_id": 5,
      "natural_task_hash": "sha256:…",
      "fixture_hash": "sha256:…",
      "repetitions": [
        {
          "rep": 1,
          "repetition_id": "…",
          "runs": {
            "candidate": {"worker_id": "w1", "session_id": "s1"},
            "reference": {"worker_id": "w2", "session_id": "s2"}
          }
        }
      ],
      "outcome": {
        "category": "both_pass",
        "regression_status": "observed_both_pass",
        "measurement_status": "inconclusive",
        "protocol_status": "limited"
      },
      "verdict": {"candidate_pass": true, "reference_pass": true},
      "assertions": [
        {
          "assertion": "Finds the reachable defect",
          "type": "behavioral",
          "scope": "shared-outcome",
          "candidate": {"pass": true, "evidence": "…"},
          "reference": {"pass": true, "evidence": "…"}
        },
        {
          "assertion": "Uses the prescribed review-point section",
          "type": "presentation",
          "scope": "skill-contract",
          "candidate": {"pass": true, "evidence": "…"},
          "reference": {"pass": false, "evidence": "…"}
        }
      ]
    }
  ]
}
```

`shared-outcome` and `universal-safety` assertions are the marginal-value
denominator. `skill-contract` assertions are reported for contract adherence
and version comparison, but they cannot make a no-skill baseline lose credit
in a qualification result. Regression status is deliberately narrow:
`observed_candidate_only_pass` means candidate passed while reference failed,
`observed_reference_only_pass` means reference passed while candidate failed,
`observed_both_pass` means both passed, and `observed_both_fail` means both
failed. `inconclusive` and `not_run` remain available for incomplete or
unavailable comparisons. The uppercase report labels are
`OBSERVED_CANDIDATE_ONLY_PASS`, `OBSERVED_REFERENCE_ONLY_PASS`,
`OBSERVED_BOTH_PASS`, and `OBSERVED_BOTH_FAIL`. These are observations, not
statistical conclusions; repeated independent runs are required before making
an improvement claim. The old labels remain readable as compatibility aliases.

## Optional strict confirmation result (legacy Docker adapter)

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
    "target_guidance_present": "activation probe confirmed .kilo/skills/code-review/SKILL.md present and hash-matched",
    "target_guidance_hash": "sha256:…",
    "target_absent_in_baseline": "boundary probe confirmed no .kilo/skills tree in baseline",
    "baseline_guidance_absent": "boundary probe confirmed no discovery tree in baseline",
    "contamination": "none",
    "conditions": ["target", "baseline", "placebo"],
    "repeats": 3,
    "activation_mechanism": "kilo-command-skill",
    "runtime_treatment_paths": [".kilo/skills"],
    "target_skill_kilo_path": ".kilo/skills/code-review",
    "placebo_skill_kilo_path": ".kilo/skills/security-review",
    "target_skill_activated": true,
    "placebo_skill_activated": true,
    "target_skill_context_probe": "present",
    "placebo_skill_context_probe": "present",
    "activation_events": [
      {"tool": "skill", "skill_name": "code-review", "timestamp": "…", "session_id": "…"}
    ]
  },
  "cases": [
    {
      "case_id": 1,
      "natural_task_hash": "sha256:prompt-hash-case-1",
      "fixture_hash": "sha256:fixture-hash-case-1",
      "raw_evidence_hash": "sha256:evidence-file-hash-case-1",
      "repetitions": [
        {
          "rep": 1,
          "repetition_id": "550e8400-e29b-41d4-a716-446655440001",
          "runs": {
            "target":   { "session_id": "t1", "container_id": "ct1" },
            "baseline": { "session_id": "b1", "container_id": "cb1" },
            "placebo":  { "session_id": "p1", "container_id": "cp1" }
          }
        },
        {
          "rep": 2,
          "repetition_id": "550e8400-e29b-41d4-a716-446655440002",
          "runs": {
            "target":   { "session_id": "t2", "container_id": "ct2" },
            "baseline": { "session_id": "b2", "container_id": "cb2" },
            "placebo":  { "session_id": "p2", "container_id": "cp2" }
          }
        },
        {
          "rep": 3,
          "repetition_id": "550e8400-e29b-41d4-a716-446655440003",
          "runs": {
            "target":   { "session_id": "t3", "container_id": "ct3" },
            "baseline": { "session_id": "b3", "container_id": "cb3" },
            "placebo":  { "session_id": "p3", "container_id": "cp3" }
          }
        }
      ],
      "outcome": {
        "category": "placebo_only_pass",
        "measurement_status": "non_discriminating",
        "protocol_status": "valid"
      },
      "verdict": { "target_pass": false, "baseline_pass": false, "placebo_pass": true },
      "assertions": [
        {
          "assertion": "<frozen assertion text, verbatim from evals.json>",
          "target":   { "pass": true,  "evidence": "quoted span / diff line / exit code" },
          "baseline": { "pass": false, "evidence": "quoted span / diff line / exit code" },
          "placebo":  { "pass": true,  "evidence": "quoted span / diff line / exit code" }
        }
      ]
    }
  ]
}
```

**Key provenance rules for execution results:**

- **Per-case `natural_task_hash` is required.** Each `cases[].natural_task_hash` must equal
  `sha256(current_case["prompt"].encode("utf-8"))` using exactly the runner's hashing
  convention. The validator loads the authoritative `evals.json`, finds `case_id`, recomputes
  the source prompt hash, and requires an exact match. A single top-level
  `protocol.natural_task_hash` cannot represent three different prompts. For multi-case
  result files, the top-level `protocol.natural_task_hash` must be absent; for single-case
  files it may be present but then must match the sole case's hash. If a top-level
  `natural_task_hash` is retained for backward compatibility, it must be a clearly named
  aggregate (e.g., `case_task_hashes`) or removed — do not keep an ambiguous single hash
  that pretends to represent several different tasks. The validator fails closed on mismatch.
- **Per-case `fixture_hash` and optional `raw_evidence_hash`:** Each protocol-valid
  execution case MUST record its `fixture_hash` (the frozen fixture hash from
  `evals.json`) and, when available,
  `raw_evidence_hash` (SHA-256 of the canonical raw evidence file that produced the case
  summary, e.g., `.eval-evidence/exec-<skill>-case<id>.json`). The raw file remains
  ignored/local, but someone with the raw evidence can verify it matches the committed
  summary's source. Calculate the hash from a stable canonical file, not a mutable temp.
  Limited or invalid historical records may omit the new per-case fields, but they
  cannot claim `protocol_status: valid` without them.
- **Per-case/per-repetition execution identity:** Single `protocol.runs` / top-level `runs`
  cannot provenance-identify 27 condition executions. Each `cases[].repetitions[]` entry
  must contain `rep`, `repetition_id` (stable UUID or hash unique per repetition), and
  `runs` with the declared `target`/`baseline` conditions (and `placebo` when
  declared), each having `session_id` and `container_id`.
  Sanitized IDs are okay if the project intentionally shortens them, but they must remain
  uniquely traceable to the local ignored evidence. The validator checks:
  - repetition count matches the declared repeat count;
  - each repetition contains all required conditions;
  - `repetition_id` values are unique across repetitions;
  - `session_id` values are unique across all independent condition executions;
  - `container_id` values are unique across all independent condition executions;
  - duplicate session/container/repetition IDs fail;
  - the `Repeats = 3` claim is mechanically supported by this structure.

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

## Optional Docker execution evidence (legacy Layer B adapter, local)

The following section documents the repository's retained strict Docker/Kilo
adapter. It is intentionally optional; the harness-neutral adapter contract
above is the default for new smoke, qualification, and regression records.

For `evaluation_mode: "execution"` the worker runs in **fresh Docker containers**
(see `isolation-protocol.md` and `Dockerfile.eval`), so the run can be
`protocol.status: valid` with genuine OS-level isolation. The raw runner evidence
(`scripts/run_execution_eval.py`) is written to `.eval-evidence/exec-<skill>-case<id>.json`
(gitignored) with top-level `"evidence_type": "execution"` and **one repetition
per independent seed copy**.

Each repetition MUST prove:

- **Independent starting state (TASK state).** The runner derives one pristine
  seed, then makes one independent copy per condition and records
  `starting_task_hash` for each. TASK-state hashes EXCLUDE the evaluator
  runtime treatment paths (`runtime_treatment_paths`) — the exact ordered list
  emitted by `scripts/run_execution_eval.py` (currently only `.kilo/skills`).
  The target/placebo discovery trees are intentionally different from the
  baseline, so hashing them together and requiring equality would fail by
  construction; adding broader exclusions such as `.kilo`, `src`, or `tests`
  is invalid.
  The validator requires all `starting_task_hash` values to equal the frozen
  `canonical_task_seed_hash` / `expected_fixture_hash`. The full-filesystem
  hashes (`starting_full_hash` / `ending_full_hash`) are recorded SEPARATELY so
  the treatment difference is visible without invalidating task equality.
  The condition workers therefore begin from byte-identical task state and can
  never share a mutable fixture.
- **Repetition identity.** Each repetition carries a stable `repetition_id`
  (UUID or hash, unique per repetition) and `rep` index. All condition data
  for a repetition must reside in one repetition object; the validator requires
  that the three conditions for a repetition came from the SAME runner repetition
  / pristine seed generation. Condition-level splicing (e.g., taking `target`
  from old rep 1, `placebo` from replacement run) is rejected — a failed
  condition invalidates the entire repetition, and the replacement must be a
  complete fresh `target`/`baseline`/`placebo` triplet. Duplicate `repetition_id`,
  `session_id`, or `container_id` values across supposedly independent
  executions fail.
- **Distinct execution.** `conditions.target.container_id` ≠
  `conditions.baseline.container_id` (and ≠ `conditions.placebo.container_id`
  when a placebo is present), and likewise for `session_id`. This is verified
  per-repetition via `distinct_containers` / `distinct_sessions`, and the
  committed result's per-repetition `runs` are checked for cross-repetition
  uniqueness.
- **Controlled post-activation (not routing).** Layer B does NOT test whether
  Kilo's router chooses to activate the guidance. The evaluator ACTIVATES the
  target and placebo guidance through the same deterministic mechanism:
  `kilo run --command <skill>:skill`, which resolves against the discovery
  tree `conditions.<name>.skill_kilo_path` (`.kilo/skills/<name>/`) inside the
  worker workspace and injects the skill body into context at session start.
  An unresolvable command makes kilo exit non-zero, so a successful run
  (returncode 0) is machine-verifiable proof the skill was discovered and
  injected. `conditions.<name>.activation_mechanism` is
  `"kilo-command-skill"` for target/placebo and `"none"` for baseline.
- **Source anchoring.** Execution evidence records the canonical
  `fixture_source_path`, `fixture_path`, `fixture_source_hash`, and
  `target_skill_source_path`; the validator recomputes these against the current
  repository artifacts. Placebo guidance hashes are likewise checked against
  the current canonical placebo skill tree.
- **Activation boundary (probed inside the container).**
  `conditions.target.skill_probe` is `"present"` only if an in-container probe
  found `.kilo/skills/<name>/SKILL.md` present AND content-hash-matched;
  `conditions.baseline.skill_probe` is `"absent"` only if the probe confirmed
  no `.kilo/skills` tree at all. Target and placebo also require
  `skill_context_probe: "present"`: the runner exports the completed Kilo
  session inside the container and checks that the full guidance body (after
  frontmatter) appears in the serialized user-context message. Mere file
  presence is never activation.
  When the model ALSO issues a native `skill` tool call, the parsed
  `activation_events` (real completed `tool_use` events with
  `part.tool == "skill"`, matching `state.input.name`, and a
  `<skill_content>` result) are recorded as supplementary evidence; an event
  naming a different skill does not count.
- **Failure is not evidence.** If the Docker/Kilo invocation returned non-zero, the
  container never started, the model output was empty/unparseable, or no session id
  was produced, the condition's `run_status="failed"` and the validator
  **rejects** the file. `returncode` must be `0` for all conditions. A
  repetition with any failed condition is invalid and must be discarded in full;
  the replacement must be a complete fresh triplet.
- **Task-state mutation recorded.** `conditions.<name>.ending_task_hash`
  proves what each worker changed relative to `starting_task_hash`.
  Optional filesystem snapshots
  (`conditions.<name>.filesystem_snapshot_before/after`) capture the concrete
  diff. The `natural_task_identical_across_conditions` flag confirms the task
  text was byte-identical across conditions.

The validator dispatches on `evidence_type` and checks the file with
`python3 scripts/validate_evaluations.py --check-evidence`; unknown/malformed
evidence is a hard error, never silently skipped.

## Required identity

- `skill` — must match a discovered `evals.json` `skill_name`.
- `evaluation_mode` — `execution` (Layer B), `regression` (candidate/reference),
  or `routing` (harness selection). Catalog-discriminability (Layer A)
  evidence is stored as `evidence_type: "catalog-routing"` in the local
  evidence dir, not in committed result files; it produces confusion-set
  confusion matrices, not per-case routing verdicts.
- `method` — `harness-adapter` (the neutral execution/regression path),
  `docker-isolated` (the optional strict confirmation adapter), or
  `harness-routing` (Layer C, routing). `prompt-injection-approximation` is
  historical/`invalid`.
- `case_revision` — commit/content hash of the `evals.json` used.
- `fixture_revision` — commit/content hash of the fixture (`designed_only` if none).
  For multi-case execution results, `fixture_revision` at the top level is a
  summary; each `cases[].fixture_hash` must match the frozen hash for that case.
  For harness-neutral regression evidence, it is the resolved reference Git
  revision named by `case_anchors.reference`, which supplies the shared fixture.
- `case_anchors` — required for harness-neutral regression evidence; the
  `candidate` and `reference` entries independently bind each revision's case,
  prompt, fixture declaration, and generator source (when applicable).
- `candidate_skill_hash` / `reference_skill_hash` — content hashes of the
  worker-visible guidance trees at their recorded revisions.
- `case_set_hash` — canonical hash of both revision-local case anchors.
- `fixture_hash` — hash of the exact shared worker-visible fixture.
- `runner_version` — version of the regression metadata/validation contract.
- `reproduction_status` — `reproducible` or
  `invalid_reproduction_environment`; the latter is never a pass.
- `target_skill_revision` — commit hash of the `SKILL.md` under test.

## Runtime block

`harness`, `model`, `reasoning_effort`, `tool_policy`, `network_policy`,
`isolation_method` are all required in committed result metadata. Their values
may be adapter-defined; `harness_version` may be `"unknown"` when not
discoverable. A `valid` execution/regression run still requires a verified
OS-level boundary. Adapter-managed local workers should be marked
`protocol_status: limited` unless the adapter proves that boundary.

## Protocol block

- `status` — `valid`, `limited`, `contaminated`, `invalid`, `not_run`.
- `tier` — `tier-1-fast-dev`, `tier-2-strict-isolated`, or `tier-3-harness-native`.
- `worker_isolation_verified` — boolean; how (boundary probe). A `valid` run
  requires it `true`.
- `isolation_attestation` — structured evidence for a valid execution or
  regression comparison. It must be independently obtained, declare an
  `os-level` boundary, match `runtime.isolation_method`, and bind every case
  ID to its `raw_evidence_hash`. Missing or mismatched attestation means the
  comparison cannot claim `valid`.
- `execution_verified` — optional boolean claim about the execution boundary.
  It is accepted only when every condition's raw
  `execution_attestation.confidence` is `runtime_verified` or
  `independently_verified`; `adapter_declared` is valid limited evidence but
  cannot support this claim. `attestation_confidence` records the aggregate
  level used by a committed result.
- `guidance_id`, `guidance_hash`, `guidance_source` — condition-level identity
  fields in raw neutral evidence. `activation_verified` and
  `context_verified` must both be true for a guided condition. Legacy Kilo
  placement fields may be retained as adapter metadata, but they are not part
  of the neutral activation contract.
- `target_guidance_present` — evidence (manifest/log/probe) that the target
  worker received the intended guidance identity and entered it into context.
  **Required for execution runs**; must be `null` for routing runs.
- `target_guidance_hash` — the generic guidance hash the target condition
  received. **Required for execution runs.** A legacy adapter may retain its
  discovery-path or command evidence as optional metadata.
- `target_absent_in_baseline` — evidence that the baseline did **not** receive
  the target skill's identity or text. **Required for execution runs.**
- `baseline_guidance_absent` — evidence the baseline did not receive the target
  guidance identity or context. Provider- or filesystem-specific absence
  probes are optional supporting metadata.
- `contamination` — `none` or a description.
- `natural_task_identical_across_conditions` — `true` only when the runner
  verified the worker-visible prompt hash is identical across all conditions.
  Deprecated for multi-case results: use per-case `natural_task_hash` instead;
  top-level `natural_task_hash` must be absent for multi-case files (or be a
  clearly named aggregate). The validator fails if a multi-case file has an
  ambiguous single prompt hash at the top level.
- `natural_task_hash` — SHA-256 of the exact current source eval-case prompt;
  the validator rejects hashes from a stale or otherwise different prompt.
  **Per-case `cases[].natural_task_hash` is required for execution results** and
  must equal `sha256(prompt.encode("utf-8"))` for that case's current prompt.
  For single-case results a top-level `protocol.natural_task_hash` may be used;
  for multi-case results the top-level must be absent.
- `routing_mechanism` — **required for routing runs**: how the selected skill
  was captured (harness manifest, startup log, named tool-call). Absent/unknown
  ⇒ the routing claim is invalid, never a routing conclusion.
- `conditions` — list of condition names used. Protocols currently use
  `target`/`baseline`/`placebo` or `candidate`/`reference` as defined above.
- `repeats` — positive integer number of repetitions claimed for each execution
  case. A protocol-valid result must declare this explicitly, and every case's
  `repetitions` list must contain exactly that many entries with `rep` indices
  `1..repeats`.

## Per-case grades

- `outcome.category` — `skill_only_pass`, `baseline_only_pass`, `both_pass`,
  `both_fail`, `placebo_only_pass`, `non_discriminating`, `invalid`, `not_run`.
- For `evaluation_mode: "regression"`, use `candidate_only_pass`,
  `reference_only_pass`, `both_pass`, or `both_fail` and add
  `outcome.regression_status` (`observed_candidate_only_pass`,
  `observed_reference_only_pass`, `observed_both_pass`,
  `observed_both_fail`, `inconclusive`, or `not_run`). `both_fail` maps to
  `observed_both_fail`: it is an observation that neither revision passed, not
  a statistical conclusion. The pre-v2 labels remain readable as aliases. Do not use
  `skill_improved`, `skill_effective`, or `better_skill` as regression claims.
  `verdict.candidate_pass` and `verdict.reference_pass` are the authoritative
  booleans.
- `outcome.measurement_status` — `discriminating`, `non_discriminating`,
  `inconclusive`.
- `outcome.protocol_status` — as above.
- `verdict.target_pass` / `verdict.baseline_pass` / `verdict.placebo_pass` —
  booleans; the validator checks they are consistent with `outcome.category`:
  - `skill_only_pass` ⇔ target passes, baseline fails, placebo fails
  - `baseline_only_pass` ⇔ target fails, baseline passes
  - `both_pass` ⇔ target and baseline both pass
  - `both_fail` ⇔ target, baseline, and placebo all fail
  - `placebo_only_pass` ⇔ target fails, baseline fails, placebo passes
  - `non_discriminating` ⇔ the target has no unique advantage over the
    declared controls (including a control matching or outperforming it)
- **Execution mode** — every frozen assertion from `evals.json` must appear in
  the graded `assertions` list (no assertion silently disappears). Each assertion
  grades `target` and `baseline` (and `placebo` when present) with a `pass`
  boolean; **every passing condition must carry concrete `evidence`** (quoted
  span / diff line / exit code) — plausible prose or self-assertion is not
  evidence. Each protocol-valid case must have `natural_task_hash`, `fixture_hash`,
  and `repetitions` with per-repetition `repetition_id` and `runs` as described
  above; the validator checks that `repetitions` count matches `protocol.repeats`,
  that each repetition has all declared conditions, and that session/container/
  repetition IDs are unique across the complete result. Limited or invalid
  records may retain the older compact shape, but are not valid evidence.
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
- `natural_task_identical_across_conditions` is not `true` (execution, single-case only; multi-case uses per-case `natural_task_hash`);
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
