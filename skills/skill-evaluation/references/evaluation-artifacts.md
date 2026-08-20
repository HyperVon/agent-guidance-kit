# Evaluation artifacts

Progressive-disclosure companion to `skill-evaluation`. Load this when authoring
the `evals/evals.json` case set or recording run results. The grading,
contamination, and verification *rules* stay in `SKILL.md`; this file holds
schemas and examples.

## Case schema

Store the case definitions at `evals/evals.json` inside the skill. The project
validator (see `scripts/validate_evaluations.py`) checks this shape:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "kind": "matching",
      "case_type": "smoke",
      "evaluation_modes": ["routing", "execution"],
      "prompt": "A realistic request",
      "routing_context": {
        "catalog_required": true,
        "comparison": "target-present-vs-target-absent",
        "catalog_source": "generated-from-current-catalog",
        "target_skill": "example-skill"
      },
      "routing": {
        "experiment": "target-availability",
        "target_skill": "example-skill",
        "target_present": { "expected_selected_skill": "example-skill" },
        "target_absent": { "expected_selected_skill": null,
                            "allowed_fallbacks": ["clarify", "generic-review"] }
      },
      "execution": {
        "expected_output": "Observable success criteria; not a worker-visible grading rubric",
        "assertions": [
          "a plain-string shared-outcome assertion (legacy)",
          { "text": "Finds the reachable defect", "type": "behavioral",
            "scope": "shared-outcome" },
          { "text": "Uses the skill-defined prescribed handoff", "type": "presentation",
            "scope": "skill-contract" }
        ],
        "placeholder_guidance": null
      },
      "fixture": {
        "status": "ready",
        "type": "committed",
        "path": "evals/files/case-1",
        "content_hash": "sha256:abcdef…"
      }
    }
  ]
}
```

### Fields

- `skill_name` — required; must match the skill directory name.
- `evals` — exactly 5 cases with `id`s `{1,2,3,4,5}` and a fixed `kind`
  distribution: 2 `matching`, 1 `neighboring`, 1 `ambiguous`, 1 `edge`.
- `id` — integer, exactly `{1,2,3,4,5}`.
- `kind` — one of `matching`, `neighboring`, `ambiguous`, `edge`.
- `case_type` — design-intent classification. Defaults to `"smoke"` for legacy
  packs. The discriminator family lives in confusion sets:
  `discriminator`, `hard-negative`, `misleading-keyword`, `multi-intent`,
  `ambiguous-natural`, `counterfactual`, `workflow-transition`,
  `harness-native`. A `smoke` case is cheap sanity coverage — it must not be the
  primary evidence of robust routing or execution efficacy.
- `evaluation_modes` — array with at least one of:
  - `"routing"` — harness or catalog selection; graded from harness-selection
    evidence (layer C) or the catalog-discriminability proxy (layer A). The
    `routing_context` block and `routing` oracle distinguish the experiment type.
  - `"execution"` — post-activation efficacy; graded from worker output against
    frozen assertions via the target/baseline/placebo condition comparison.
  - `"regression"` is a result protocol over an execution case, not a required
    case-mode value. It compares `candidate` and `reference` revisions using
    the same frozen task and assertions.
- `prompt` — non-empty; a natural user request (do not recite the skill's
  workflow; do not leak the expected answer or the intended defect).
- `routing` / `routing_context` — present iff `"routing"` is in the modes.
- `execution` (`expected_output` + `assertions`) — present iff `"execution"` is
  in the modes.
- `fixture` — required block:
  - `status`: `"ready"` or `"designed_only"`.
  - when `"ready"`: `type` (`"committed"` or `"generator"`), `path` (must exist
    under the skill dir), and `content_hash` are required. A `generator` fixture
    additionally records `source_hash` (the generator source) and `output_hash`
    (the deterministic generated output); the validator runs the generator and
    fails if the output is non-deterministic or the hash is wrong.
  - when `"designed_only"`: no `path`; the case is not executable yet.
  - `placeholder_guidance`: when non-null and non-empty, the execution case
    depends on guidance the worker has NOT yet been given. This is only valid
    with `fixture.status: "designed_only"`; a `ready` fixture must not declare
    placeholder guidance (it would be a false, not-yet-runnable benchmark).
- No fixture directory may contain a `catalog.md` (routing-surface leak).

### Assertion types

Assertions are either plain strings (legacy, treated as `behavioral` and
`shared-outcome`) or objects `{ "text": "...", "type": "<type>", "scope":
`"<scope>" }`. Typed assertions must carry an explicit `type`; new assertions
should carry an explicit `scope`:

- `"behavioral"` — a hard correctness invariant (must never be false, and must be
  verifiable from worker output). Soft preferences must not be typed behavioral.
- `"quality"` — a quality criterion that is desirable but not a hard correctness
  gate.
- `"presentation"` — a formatting / style preference. Never graded as a hard
  pass/fail correctness gate.

Assertion scopes are the fairness boundary:

- `"shared-outcome"` — independently justified by the natural task, shared
  artifacts, objective correctness, observable outcome, or generally applicable
  engineering constraints. This is the marginal-value denominator.
- `"skill-contract"` — behavior defined only by the target skill, such as its
  prescribed report headings, terminology, workflow order, or handoff ritual.
  Score it for contract adherence and revision comparisons; never subtract it
  from a no-skill baseline in a qualification result.
- `"universal-safety"` — a requirement that applies to every condition, such as
  not exposing secrets, claiming tests that were not run, or exceeding explicit
  authority. It may contribute to qualification alongside shared outcomes.

An omitted scope is interpreted as `shared-outcome` for backward compatibility.
The validator rejects unknown scopes and checks the scope recorded in a result
against the frozen case assertion.

A case that uses typed assertions must classify every one. The validator rejects
an assertion object with a missing or invalid `type`.

### Routing and execution are separate oracles

A routing evaluation asks *which skill did the harness select?* and is graded
from **harness-selection evidence** (loaded-skill manifest, routing log, named
tool call) — never from whether the final answer explains why some other skill
was not chosen. An execution evaluation asks *once the skill is active, did its
guidance improve the outcome?* and is graded from the worker's actual output
against the frozen assertions via the target/baseline/placebo comparison.

Therefore the two oracles live in different blocks:

- `routing` — required when `"routing"` is in the modes.
  - `experiment` — `"target-availability"` (catalog present vs absent) or
    `"description-regression"` (candidate description vs prior description).
  - `target_skill` — the skill under test.
  - `target_present.expected_selected_skill` — the skill the router should pick
    when the target is in the catalog. For a `matching` case this is the target;
    for `neighboring` it is the correct **owner**; for `ambiguous` it is `null`
    with `allowed_behavior: ["clarify", "select-owner-with-documented-tiebreaker"]`.
  - `target_absent.expected_selected_skill` — the expected selection when the
    target is **removed** from the catalog. For `matching` this is normally `null`
    (fallbacks allowed); for `neighboring` the owner is unchanged because only the
    target was removed; for `ambiguous` it is `null` with clarifiers.
- `execution` — required when `"execution"` is in the modes; holds
  `expected_output` and `assertions` (verifiable from worker output only).

A routing-only case must **not** carry an `execution` block (no handoff-prose
assertions), and an execution-only case must **not** carry `routing` /
`routing_context`. This is what stops a post-activation handoff oracle from
being mistaken for a routing result.

### routing_context

Routing cases declare `routing_context`:

- `catalog_required: true` — the harness routing surface (catalog) is needed.
- `comparison` — `"target-present-vs-target-absent"` (default) or
  `"description-regression"`.
- `catalog_source: "generated-from-current-catalog"` — the catalog is produced
  by `scripts/build_routing_catalog.py` from each skill's frontmatter, **not**
  copied into the task fixture.
- `target_skill` — must equal the skill name.

The catalog is the **routing projection** and is generated per condition
(`--target-absent <skill>` for the baseline). It must never be committed inside
a task fixture, because the same task fixture is reused across conditions and
only the projection differs.

### Shared cross-skill cases

Discriminator-class cases that are hardest to get right are stored at the
repository level, not inside a single skill:

- `evaluations/confusion-sets/<name>.json` — confusion-set cases grouped by
  cluster. Each set lists its candidate `skills` (all `expected_skill` values
  for non-ambiguous cases must appear in this list). Cases include counterfactual
  pairs (`counterfactual_pair` id) and multi-turn workflow transitions. Every
  case prompt must avoid naming the expected skill.
- `evaluations/holdout/<name>.json` — holdout cases stored outside skill
  directories so ordinary edits do not consume them. Holdout results measure
  generalization, not development-case performance. Run them with
  `scripts/run_catalog_routing_eval.py --holdout
  evaluations/holdout/<name>.json --out ...`; the runner records
  `evidence_type: "holdout"` and never writes them into development benchmark
  outputs.

Workflow-transition and harness-native cases carry per-turn `expected_route`
values. `expected_route` is REQUIRED on every turn: a skill name from the
case-set's `skills` list, or explicit `null` meaning **"no specialized skill
expected"** (ordinary unspecialized work — e.g. generic implementation — must
not be encoded as any skill; `implementation-planning` explicitly stops before
implementation). A missing `expected_route` key is a schema error, never
treated as `null`, and is graded distinctly from an explicit null route (the
model must decline a specialized skill — return a null selection).

Counterfactual cases must live in a confusion-set file (never inside a skill's
own eval pack), because the paired case must not be visible in the same context.

## Runner evidence files (layer B, local)

For `evaluation_mode: "execution"` the raw runner evidence is written to
`.eval-evidence/exec-<skill>-case<id>.json` (gitignored) with top-level
`"evidence_type": "execution"` and **one repetition per independent seed copy**.
The core schema is harness-neutral. A runner may use the JSON adapter contract
in [`harness-adapter.md`](../../../docs/evaluations/harness-adapter.md) or
another explicitly documented adapter.
The validator's `--check-evidence` gate dispatches on `evidence_type` and rejects
unknown/malformed files as hard errors.

Each execution repetition MUST prove:

- **Independent starting state (TASK state).** One pristine seed, then one
  independent copy per condition. All `starting_task_hash` values must equal
  `canonical_task_seed_hash` / `expected_fixture_hash`. TASK-state hashes
  exclude the evaluator runtime treatment paths (recorded in
  `runtime_treatment_paths`, e.g. the neutral adapter's
  `.evaluation-runtime/guidance` (or the optional legacy adapter's
  `.kilo/skills`) so target/placebo treatment trees cannot invalidate seed
  equality; full-filesystem hashes are recorded separately
  (`starting_full_hash` / `ending_full_hash`).
- **Distinct execution.** Distinct worker IDs and session IDs per condition.
  A container ID is optional adapter metadata, not a core requirement.
- **Controlled post-activation.** Layer B does NOT test whether the router
  activates the guidance. The evaluator activates target/placebo guidance
  through the same harness adapter mechanism and records
  `activation_mechanism`, `guidance_path`, and `guidance_content_hash`. The
  adapter must use an identical activation procedure for the compared
  conditions; provider- or CLI-specific fields are optional metadata.
- **Activation boundary (adapter-probed).**
  `conditions.<name>.guidance_probe` is `"present"` only when the adapter
  verified that the intended guidance was available and content-hash-matched;
  a guided condition also requires `guidance_context_probe: "present"` to prove
  that the guidance entered worker context. Mere file presence is never
  activation. Harness-native event logs may be retained under adapter metadata
  but are not part of the core schema.
- **Failed runs are rejected.** A non-zero return code, missing worker/session
  identity, or empty output is `run_status="failed"` and invalidates the
  evidence file.
- **Identical natural task.** `natural_task_hash` is identical across all
  conditions; `natural_task_identical_across_conditions` must be `true`. The
  worker-visible prompt never names the skill, condition, or evaluation.
- **Task-state mutation recorded.** `ending_task_hash` plus a filesystem
  snapshot prove what each worker actually changed.
- **Source anchoring.** Execution evidence records the canonical fixture/evals
  paths and source hash, plus the target skill source path; the validator
  recomputes those values from the current repository. A placebo hash must also
  match the current canonical placebo discovery tree.

Catalog-discriminability evidence (`evidence_type: "catalog-routing"`,
`"confusion-set"`, or `"holdout"`) is
produced by `scripts/run_catalog_routing_eval.py` and carries, per case set, an
`aggregate` block with the full intended-vs-selected confusion matrix and
per-skill precision/recall (counting rule: one observation per successful model
decision; workflow-transition turns each contribute one observation; explicit
null selections are the literal `"null"` class; precision/recall are `null` —
not 0 — when the denominator is zero). Case-set evidence is additionally bound
to its canonical `case_set_path` and `case_set_hash`, including the source skill
list and case metadata. It is a proxy only — it does not replace an actual
harness-selection log at Layer C.

## Regression evidence (layer B, local)

`scripts/run_skill_regression_eval.py` is a thin workflow over the neutral
harness adapter. It materializes `candidate` and `reference` skill revisions
from Git, creates independent copies of one frozen fixture, and records
`evidence_type: "regression"` with `protocol: "regression"`. Both conditions
must use the same natural task, model/runtime settings, activation procedure,
and adapter contract. Neither condition is a no-skill baseline.

The required per-condition fields are `worker_id`, `session_id`,
`guidance_probe`, `guidance_context_probe`, `guidance_path`, and
`guidance_content_hash`. A `container_id`, provider name, image, CLI version,
or other harness-specific field may be added as adapter metadata but is not
required by the regression protocol.

## Recording a run

When a run is executed, record the result so the evaluation record stays current.
The human interface is conversation for routine runs, but a manual CLI/Docker
path is documented in `docs/evaluations/RUNBOOK.md` when direct execution is
needed. The agent runs the commands and the human does not need to run scripts
manually for routine cases.

1. Determine `harness`, `model`, and `reasoning_effort` from runtime metadata when
   available. **If you cannot definitively determine the harness, model, or effort
   level, ask the user explicitly** and do not guess. Effort can dramatically change
   results, so always record the actual `reasoning_effort` (or the adapter-defined
   value when the harness does not expose one).
2. Write a result file under a results directory of the project's choosing (for
   example `docs/evaluations/results/`) following the schema in
   [`docs/evaluations/result-schema.md`](../../../docs/evaluations/result-schema.md)
   — include the confirmed adapter/runtime metadata and the protocol-specific
   verdicts (`target`/`baseline` or `candidate`/`reference`) plus the decision.
   Keep raw outputs in an ignored workspace; only sanitized summaries are
   committed.
3. Update the validation matrix (`docs/evaluations/validation-matrix.md`) to link
   the results and record the `reasoning_effort`. Use `✓` when a discriminating
   run shows `target_pass` and not `baseline_pass`; `?` when the measurement is
   inconclusive or `non_discriminating`; `⚠` when a run favors the baseline; and
   `–` when not yet tested.
4. Regenerate the sanitized aggregate summary (`docs/evaluations/SUMMARY.md`) so
   the latest-per-skill aggregate stays in sync.

Results must distinguish `protocol_status` from `measurement_status`: a valid
isolated run may still be `inconclusive` or `non_discriminating` when the cases or
assertions do not discriminate the conditions. A `non_discriminating` outcome
(target and baseline both pass equally) must **not** be counted as a skill win.
