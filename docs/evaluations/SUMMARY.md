# Skill evaluation summary

> **Status: case sets designed, no runs executed yet.**

This repository previously had **zero** evaluation artifacts. As of this change, every one of the
26 skills in the catalog has a designed evaluation case set at `skills/<name>/evals/evals.json`,
following the schema in `skills/skill-evaluation/references/evaluation-artifacts.md`.

## What exists now
- **26 case sets**, 130 cases total — each skill has a 5-case pack:
  2 matching, 1 neighboring, 1 ambiguous, 1 edge/behavior.
- A `validation-matrix.md` listing every skill with status `–` (not yet tested).

## What has NOT been done
- **No runs.** No case has been executed against a WITH-SKILL or BASELINE worker. Per
  `skills/skill-evaluation`, a valid run requires two independently isolated workers; this CLI environment
  provides no OS-level isolation, so no trustworthy comparison can be produced here yet.
- **No fixtures.** Case `files` arrays are intentionally omitted; fixtures must be authored at run time.
- **No efficacy claims.** Nothing here asserts any skill is effective or verified.

## Agreed run target (for when runs happen)
- Harness: **Kilo/CLI** (subagents produced with the same model as the orchestrating agent)
- Model: **hy3-free**
- Reasoning effort: **high**

## How evaluations are run
The working method is documented in [`RUNBOOK.md`](RUNBOOK.md): directory isolation +
fresh subagents (WITH-SKILL vs BASELINE), fixture-building guidance, grading rubric, and the
isolation limitation. Future agents should follow it rather than rediscover the setup.

## Pilot (code-review)
A method-validation run is recorded in [`results/code-review.md`](results/code-review.md).
Headline: defect-finding cases did **not** discriminate (base models already review well),
but the **routing/boundary** case did — `code-review` correctly handed off a redesign
question to `architecture-review` while the baseline answered in-place. This confirms the
skill's value is in boundaries, and shapes how the remaining cases should be built
(hard, fair, boundary-focused — not rigged).

## Second skill (git-github-workflow)
Case 3 (neighboring) is recorded in [`results/git-github-workflow.md`](results/git-github-workflow.md).
It did **not** discriminate — and exposed a real skill gap: `git-github-workflow` lists
"code review of diff content" as a non-goal but does not *actively route* to `code-review`,
so a guided worker reviewed the diff anyway. Flagged as a skill-improvement candidate.

## Next step
Execute the case sets in a harness that can provide isolated workers, then record per-skill results in
`docs/evaluations/results/` and refresh `validation-matrix.md` and this summary.
