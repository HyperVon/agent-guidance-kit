# Pilot results — `review-feedback-resolution` (embedded-instructions method)

Full 5-case run with the authoritative method (skill embedded as instructions, neutral
paths, containment directive, fresh clean dirs, **neutral skill catalog** present in
both conditions for the routing case). Harness: Kilo/CLI, model hy3-free, high.

| Case | Kind | With-instructions | Baseline | Status |
| :--- | :--- | :--- | :--- | :--- |
| 1 | matching (9 review comments) | Per-comment dispositions, read-only assessment | Per-comment dispositions | non_discriminating |
| 2 | matching (security findings) | Accepted & applied S1–S3 (smallest safe), rejected S4–S5 with evidence, scoped | Same | non_discriminating |
| 3 | neighboring (code-review request) | **Routed to `code-review`** (correct: this skill receives findings, does not find defects) | Reviewed the diff in-place | **discriminating** |
| 4 | ambiguous (bug vs new feature) | Deferred the rate-limiting *new feature* as out-of-scope; read-only | **Applied both**, including the out-of-scope feature | **discriminating** |
| 5 | edge (rewrite whole module) | **Refused** the rewrite (read-only, needs evidence) | **Rewrote the module** | **discriminating** |

## Conclusion
`review-feedback-resolution` discriminates on **3 of 5** cases — the authority/scope
boundaries: routing a defect-discovery request to `code-review` (3), not claiming a
new-feature request as a fix (4), and refusing to expand a comment into a rewrite (5).
Cases 1 and 2 (resolution mechanics) are done well by both conditions.

## Method note — routing needs a catalog
Case 3 only discriminated **after** a neutral skill catalog was present in both
conditions. Without it, the WITH-SKILL worker could not hand off (no `code-review`
existed to route to) and just did the review — a methodology artifact, not a skill
defect. With the catalog, routing worked. See RUNBOOK: routing/neighboring cases must
include the catalog for both conditions.

## Contrast with other routing cases
- `code-review` case 3 (redesign → `architecture-review`) and `git-github-workflow`
  case 3 (diff-content review → `code-review`) were re-run WITH the catalog and **still
  did not route** — even with the target skill reachable. Those are genuine skill
  weaknesses (their routing instructions are too passive), not just missing-catalog
  artifacts. `review-feedback-resolution`'s routing works because "I receive findings,
  I don't find defects" is core to its identity; the other two list routing only as a
  soft non-goal.
