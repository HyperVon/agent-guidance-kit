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

## Methodology (settled)
Directory isolation + fresh subagents; the skill is **embedded as instructions** (not an
optional file, which under-activates it); neutral paths; a containment directive; and a
**neutral skill catalog for routing/neighboring cases** (both conditions get it, so
hand-off is actually possible). Fixtures are deleted after collection. Full method in
[`RUNBOOK.md`](RUNBOOK.md). Earlier leaky runs and the optional-`guide.md` runs are
retracted as tainted / under-activating.

## Piloted skills (3 of 26)
- `code-review` (5/5): discriminates only on the **merge/approve boundary** (case 5).
  Defect-finding is non-discriminating; routing case 3 still does not route *with* the
  catalog → genuine skill weakness.
- `git-github-workflow` (5/5): discriminates on **3/5** (publish-gate discipline,
  identity safety, not claiming the dependency-upgrade workflow). Routing case 3 still
  does not route *with* the catalog → genuine skill weakness.
- `review-feedback-resolution` (5/5): discriminates on **3/5** (route defect-discovery
  to `code-review`, defer new-feature requests, refuse a module rewrite). Cases 1–2
  (resolution mechanics) are non-discriminating.

## Routing caveat
A routing case only discriminates if the target skill is reachable. Without a catalog it
cannot be, so "no hand-off" is a methodology artifact — `review-feedback-resolution` case
3 routes correctly once the catalog is present. Where routing still fails *with* the
catalog (`code-review` / `git-github-workflow` case 3), it is a real skill weakness to
fix (their routing lines are too passive).

## Next step
Continue the remaining 23 skills with the same method, recording per-skill results in
`docs/evaluations/results/` and refreshing `validation-matrix.md`.
