# Evaluation artifacts

Progressive-disclosure companion to `skill-evaluation`. Load this when authoring
the `evals/evals.json` case set or recording run results. The grading,
contamination, and verification *rules* stay in `SKILL.md`; this file holds
schemas and examples.

## Case schema

Store the case definitions at `evals/evals.json` inside the skill. The project
validator accepts this compact shape:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "kind": "matching",
      "prompt": "A realistic request",
      "expected_output": "Observable success criteria; not a worker-visible grading rubric",
      "assertions": ["A concrete property to verify"],
      "files": ["evals/files/fixture.txt"]
    }
  ]
}
```

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
discriminate the conditions.
