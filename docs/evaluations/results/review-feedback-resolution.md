# Pilot results — `review-feedback-resolution` (HISTORICAL / EXPLORATORY — protocol-invalid)

> **Status: `protocol_status: invalid` / `decision: exploratory`.** Produced
> under the earlier mixed methodology (force-injected target skill for all cases;
> instruction-only containment; condition-labeled prompts; a neutral catalog was
> added only for the routing case). Cannot establish **routing** quality as a
> harness-selection measurement. Retained as exploratory historical evidence
> only. A protocol-valid rerun (routing via real harness selection; execution via
> deliberate activation; frozen fixtures; ≥3 reps) is pending.

## Exploratory observations (to be re-verified)

| Case | Kind | With-instructions | Baseline | Measurement |
| :--- | :--- | :--- | :--- | :--- |
| 1 | matching (9 review comments) | Per-comment dispositions | Per-comment dispositions | non_discriminating |
| 2 | matching (security findings) | Accepted/applied smallest-safe, rejected others | Same | non_discriminating |
| 3 | neighboring (code-review request) | **Routed to `code-review`** (with catalog present) | Reviewed in-place | candidate execution/neighbor discriminator |
| 4 | ambiguous (bug vs new feature) | Deferred new-feature as out-of-scope | Applied both | candidate execution discriminator |
| 5 | edge (rewrite whole module) | **Refused** the rewrite | **Rewrote the module** | candidate execution discriminator |

## Interpretation under corrected methodology

- **Cases 3, 4, 5** are candidate **execution** discriminators around
  authority/scope boundaries (handing a defect-discovery request to `code-review`;
  not claiming a new-feature request as a fix; refusing to expand a comment into a
  rewrite). They require re-verification under the execution protocol with frozen
  fixtures and ≥3 repetitions.
- **Case 3 as a routing case** was only tested by force-injecting the target skill
  *and* adding a neutral catalog, so it measures post-activation handoff, not
  harness routing. The brief's corrected protocol requires routing to be measured
  by real harness selection. Whether the *router* would select
  review-feedback-resolution for a defect-discovery request, and would *not*
  select it for a neighbor, is untested. The earlier "routing worked" claim is
  therefore retracted as a routing conclusion and preserved only as a
  post-activation handoff observation.
- Cases 1 and 2 are non_discriminating (both conditions performed resolution
  mechanics well).

## Required rerun conditions before any `valid` claim

1. Frozen committed fixtures for cases 3, 4, 5 (and 1, 2 for completeness) with
   `content_hash`.
2. Routing cases run via real harness selection with selected-skill captured;
   execution cases via deliberate activation.
3. Optional irrelevant-guidance placebo.
4. ≥3 independent repetitions per condition.
