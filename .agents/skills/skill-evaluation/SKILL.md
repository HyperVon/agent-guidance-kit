---
name: skill-evaluation
description: >-
  Design or run clean-context evaluations for a project skill, comparing its
  behavior with no skill or a previous version using realistic matching,
  neighboring, and ambiguous prompts. Use when creating, revising, or deciding
  whether a skill materially improves agent outcomes.
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
  or treating one model run as proof of universal quality.
- **Side effects:** write only to an explicitly chosen evaluation workspace;
  never place generated outputs or private inputs in the catalog by default.

## Design the cases

Start with at least three realistic prompts:

1. **matching** — clearly belongs to the skill;
2. **neighboring** — belongs to a nearby skill or ordinary workflow;
3. **ambiguous** — requires clarification or a stated routing tie-breaker.

Each case needs a stable `id`, `kind`, `prompt`, and observable
`expected_output`. Add objective `assertions` for properties that can be
verified from the output. Use realistic paths and constraints, but do not add
credentials, personal data, or live external targets.

## Run and compare

1. Snapshot the current skill before changing it when comparing versions.
2. Run each case in a clean context with the skill and with the chosen
   baseline—no skill or the previous version. Keep prompts, inputs, and output
   locations equivalent.
3. Grade every assertion with concrete evidence from the output or a
   deterministic checker. Do not award a pass because the output sounds
   plausible.
4. Record timing and token data when the harness exposes it, while treating
   those measurements as environment-specific.
5. Perform human review of the outputs for usefulness, unnecessary work,
   misleading confidence, and side effects that assertions missed.
6. Improve only the smallest validated gap, then rerun the full case set. If
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
      "assertions": ["A concrete property to verify"]
    }
  ]
}
```

Keep generated results in a temporary or explicitly named workspace. Do not
claim a skill is verified when cases were only designed, not executed and
graded.

## Report and stop condition

Report the cases, baseline, execution status, assertion evidence, human-review
notes, context or token trade-off, and the keep/revise/merge/defer/reject
decision. Stop when the baseline comparison is complete or when missing
fixtures, unavailable harness behavior, or inaccessible timing data prevents
a fair comparison; state the gap instead of filling it with assumptions.
