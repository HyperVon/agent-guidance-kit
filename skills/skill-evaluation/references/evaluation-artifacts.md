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
        "assertions": ["A concrete property to verify"]
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

### Routing and execution are separate oracles

A routing evaluation asks *which skill did the harness select?* and is graded
from **harness-selection evidence** (loaded-skill manifest, routing log,
named tool call) — never from whether the final answer explains why some other
skill was not chosen. An execution evaluation asks *once the skill is active,
did its guidance improve the outcome?* and is graded from the worker's actual
output against the frozen assertions.

Therefore the two oracles live in different blocks:

- `routing` — required when `evaluation_modes` contains `"routing"`.
  - `experiment` — `"target-availability"` (catalog present vs absent) or
    `"description-regression"` (candidate description vs prior description).
  - `target_skill` — the skill under test.
  - `target_present.expected_selected_skill` — the skill the router should pick
    when the target is in the catalog. For a `matching` case this is the target;
    for `neighboring` it is the correct **owner**; for `ambiguous` it is `null`
    with `allowed_behavior: ["clarify", "select-owner-with-documented-tiebreaker"]`.
  - `target_absent.expected_selected_skill` — the expected selection when the
    target is **removed** from the catalog. For `matching` this is normally
    `null` (fallbacks allowed); for `neighboring` the owner is unchanged because
    only the target was removed; for `ambiguous` it is `null` with clarifiers.
- `execution` — required when `evaluation_modes` contains `"execution"`;
  holds `expected_output` and `assertions` (verifiable from worker output only).

A routing-only case must **not** carry an `execution` block (no handoff-prose
assertions), and an execution-only case must **not** carry `routing` /
`routing_context`. This is what stops a post-activation handoff oracle from
being mistaken for a routing result.

### routing_context (replaces `requires_catalog`)

`requires_catalog` is removed. Routing cases instead declare `routing_context`:

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

### Field rules enforced by the validator

- `skill_name` — required; must match the skill directory name.
- each `evals` entry:
  - `id` — integer, exactly the set `{1,2,3,4,5}` across the five cases.
  - `kind` — one of `matching`, `neighboring`, `ambiguous`, `edge`; the pack is
    exactly 2 `matching`, 1 `neighboring`, 1 `ambiguous`, 1 `edge`.
  - `evaluation_modes` — array with at least one of the three-layer modes:
    `routing` (legacy/harness), `catalog-routing` (Layer A: portable
    model-as-classifier over a generated neutral catalog — no harness needed),
    `harness-routing` (Layer C: optional harness-integration routing), or
    `execution` (Layer B: Docker-isolated guided vs baseline efficacy).
  - `prompt` — non-empty; a natural user request (do not recite the skill's
    workflow; do not leak the expected answer or the intended defect).
  - `routing` / `routing_context` — present iff `routing` is in the modes.
  - `execution` (`expected_output` + `assertions`) — present iff `execution` is
    in the modes.
  - `fixture` — required block:
    - `status`: `"ready"` or `"designed_only"`.
    - when `"ready"`: `type` (`"committed"` or `"generator"`), `path` (must
      exist under the skill dir), and `content_hash` are required. A `generator`
      fixture additionally records `source_hash` (the generator source) and
      `output_hash` (the deterministic generated output); the validator runs the
      generator and fails if the output is non-deterministic or the hash is
      wrong.
    - when `"designed_only"`: no `path`; the case is not executable yet.
  - No fixture directory may contain a `catalog.md` (routing-surface leak).

Keep generated results in a temporary or explicitly named workspace. Do not claim
a skill is verified when cases were only designed, not executed and graded. A
public, sanitized summary may record the harness, model, baseline, case outcomes,
evidence, limitations, and decision without committing raw model outputs or
private fixtures.

> The harness/model/effort values below are examples from a source project's eval
> harness. In a target project, substitute the actual harness, record runtime
> metadata when available, and generalize the result-schema paths; keep
> source-specific filenames in evidence-only material, not portable core.

## Recording a run

When a run is executed, record the result so the evaluation record stays current.
The human interface is conversation only (e.g. "run evals," "evaluate a skill," or
"update the eval summary"); the agent runs the commands and the human does not need
to run scripts manually:

1. Determine `harness`, `model`, and `reasoning_effort` from runtime metadata when
   available. **If you cannot definitively determine the harness, model, or effort
   level, ask the user explicitly** and do not guess. Effort can dramatically change
   results, so always record the actual `reasoning_effort`.
2. Write a result file under a results directory of the project's choosing (for
   example `docs/evaluations/results/`) following a documented schema — include the
   confirmed `harness`, `model`, `reasoning_effort`, `baseline`, per-case
   `skill_pass`/`baseline_pass`/`better`, and `decision`. Keep raw outputs in an
   ignored workspace; only sanitized summaries are committed.
3. Update a validation matrix (for example `docs/evaluations/validation-matrix.md`)
   to link the results and record the `reasoning_effort`. Use `✓` when a
   discriminating run shows `better=true`, `?` when the measurement is inconclusive,
   `⚠` when a run favors the baseline, and `–` when not yet tested.
4. Regenerate the sanitized aggregate summary (for example `docs/evaluations/SUMMARY.md`)
   so the latest-per-skill aggregate stays in sync.

Results must distinguish `protocol_status` from `measurement_status`: a valid
isolated run may still be `inconclusive` when the cases or assertions do not
discriminate the conditions. The result file schema is documented in
[`docs/evaluations/result-schema.md`](../../../docs/evaluations/result-schema.md).
