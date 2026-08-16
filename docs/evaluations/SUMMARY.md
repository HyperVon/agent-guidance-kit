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

## Next step
Execute the case sets in a harness that can provide isolated workers, then record per-skill results in
`docs/evaluations/results/` and refresh `validation-matrix.md` and this summary.
