---
name: skill-evaluation
description: >-
  Design or run clean-context evaluations for a project skill, comparing its
  behavior with no skill or a previous version using realistic matching,
  neighboring, and ambiguous prompts. Use when creating, revising, or deciding
  whether a skill materially improves agent outcomes; do not substitute it for
  authoring or reviewing a skill when measurement was not requested.
---

# Skill Evaluation

## Contract

- **Input:** a skill directory, realistic prompts, expected outcomes, optional
  fixtures, and a baseline configuration.
- **Output:** an `evals/evals.json` case set, observed outputs, assertion grades
  with evidence, and a recommendation to keep, revise, merge, or reject the
  skill.
- **Owner:** measuring skill routing and task-output value.
- **Non-goals:** deciding the skill's domain content, replacing human review,
  authoring a requested skill, or treating one model run as proof of universal
  quality.
- **Side effects:** write only to an explicitly chosen evaluation workspace;
  never place generated outputs or private inputs in the catalog by default.

## Scope gate

Use this workflow only when the user asks to measure routing or output quality.
If the request is to create or revise a skill, use `skill-authoring`; if it asks
what content is weak, use `skill-reviewer`. Do not impose an evaluation project
on a neighboring request that did not ask for measurement.

## Design the cases

Name the authoritative contract for the expected behavior, then freeze the
expected outcomes and assertions before seeing condition outputs. Do not add an
assertion merely because one condition happened to mention something useful.
If a run exposes a missing or invalid criterion, document the reason, amend the
case, and rerun every condition under the same revised case before scoring it.

Start with at least three realistic prompts:

1. **matching** — clearly belongs to the skill;
2. **neighboring** — belongs to a nearby skill or ordinary workflow;
3. **ambiguous** — requires clarification or a stated routing tie-breaker.

Each case needs a stable `id`, `kind`, `prompt`, and observable
`expected_output`. Add objective `assertions` for properties that can be
verified from the output. Use realistic paths and constraints, but do not add
credentials, personal data, or live external targets.

After the first comparison, remove assertions that pass both configurations
without distinguishing useful behavior. When routing descriptions materially
change, expand the routing set with varied should-trigger and should-not-trigger
prompts rather than overfitting the three initial cases.

## Run and compare

1. Snapshot the current skill before changing it when comparing versions.
2. Create a dedicated evaluation root containing only the declared fixtures.
   Do not use a shared temporary parent, repository collection, or workspace
   whose siblings the agent can inspect. Restrict file, tool, and network access
   to the case when the harness supports it; otherwise state the limitation and
   exclude any run contaminated by unrelated discovery.
3. Run each case in a clean context with the skill and with the chosen
   baseline—no skill or the previous version. Keep prompts, inputs, tools,
   network access, model settings, and output locations equivalent.
4. Grade every assertion with concrete evidence from the output or a
   deterministic checker. Do not award a pass because the output sounds
   plausible.
5. Record timing and token data when the harness exposes it, while treating
   those measurements as environment-specific.
6. Perform human review of the outputs for usefulness, unnecessary work,
   misleading confidence, and side effects that assertions missed.
7. Repeat cases when model variance could change the decision; do not imply
   statistical confidence from one run per condition.
8. Improve only the smallest validated gap, then rerun the full case set. If
   the skill does not beat its baseline on meaningful cases—or adds context
   cost without a demonstrated benefit—merge it into an existing owner, defer,
   or reject it.

## Evaluation file shape

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
      "expected_output": "Observable success criteria",
      "assertions": ["A concrete property to verify"],
      "files": ["evals/files/fixture.txt"]
    }
  ]
}
```

Keep generated results in a temporary or explicitly named workspace. Do not
claim a skill is verified when cases were only designed, not executed and
graded. A public, sanitized summary may record the harness, model, baseline,
case outcomes, evidence, limitations, and decision without committing raw model
outputs or private fixtures.

When a run is executed, record it in the repository so the validation matrix
stays current:

1. Write a result file under `docs/evaluations/results/` following the schema
   in `docs/evaluations/results/README.md` — include `harness` (`muse code` +
   version), `model` (`muse-spark-1.2-contributor` + provider + reasoning
   effort), `baseline`, per-case `skill_pass`/`baseline_pass`/`better`, and
   `decision`. Use `YYYY-MM-DD-<model>-<harness>.json` for multi-skill runs
   **and** its `*.md` human-readable companion (summary table + per-skill detail;
   copy `2026-08-11-muse-spark-1.2-contributor-muse-code.md`).
2. Update `docs/evaluations/validation-matrix.md` to link both the `*.json`
   and the `*.md` (`✓` when `better=true` and `skill_pass > baseline_pass`, `=`
   when both passed without discrimination, `–` when not yet tested). Keep raw
   outputs in the ignored workspace; only the sanitized summary, `*.md`, and
   `*.json` are committed.
3. Run `make check` — `scripts/validate_repository.py` validates the JSON
   shape, that each `skill_name`/`id`/`kind` matches the committed
   `evals/evals.json`, and that matrix links resolve.

## Report and stop condition

Report the cases, baseline, execution status, assertion evidence, human-review
notes, context or token trade-off, and the keep/revise/merge/defer/reject
decision. Stop when the baseline comparison is complete or when missing
fixtures, unavailable harness behavior, or inaccessible timing data prevents
a fair comparison; state the gap instead of filling it with assumptions.
