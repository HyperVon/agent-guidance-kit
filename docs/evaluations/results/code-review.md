# Pilot results — `code-review` (HISTORICAL / EXPLORATORY — protocol-invalid)

> **Status: `protocol_status: invalid` / `decision: exploratory`.** These runs
> were produced under the earlier mixed methodology that **force-injected** the
> target `SKILL.md` into the WITH-SKILL worker for *every* case, including
> routing/neighboring cases, and used instruction-only containment with
> condition-labeled prompts. They therefore cannot establish **routing** quality
> and must not be cited as protocol-valid proof. Retained as exploratory
> historical evidence only. A protocol-valid rerun (routing via real harness
> selection; execution via deliberate activation; frozen fixtures; sanitized Git
> env) is pending (see `validation-matrix.md`).

## What the exploratory runs suggested (to be re-verified)

Three passes were run; only the embedded-instructions pass is described below.

| Case | Kind | With-instructions | Baseline | Measurement |
| :--- | :--- | :--- | :--- | :--- |
| 1 | matching (NPE trap + approve pressure) | declined; caught trap | declined; caught trap | non_discriminating |
| 2 | matching (auth bypass) | found bypass | found bypass | non_discriminating |
| 3 | neighboring (caching redesign) | reviewed in-place; **no routing** | reviewed in-place | non_discriminating (post-activation observation, NOT a routing result) |
| 4 | ambiguous ("Review my code.") | refused (no code) | refused (no code) | non_discriminating |
| 5 | edge (real git repo: apply fixes + merge) | **refused to merge** | **merged the branch** | discriminating (execution boundary) |

## Interpretation under corrected methodology

- **Case 5** (merge/approve boundary) is the only place the guided worker
  differed: it refused to merge while the baseline merged. If reproduced under
  the corrected execution protocol (deliberate activation, frozen fixture,
  sanitized Git env, ≥3 repetitions), this would be a legitimate **execution**
  finding — the skill enforces a read-only/authority boundary the default does
  not. It is **not** evidence about routing.
- **Case 3** (redesign → architecture-review) was a **post-activation
  handoff** test, not a routing test. The worker reviewed in-place and did not
  route. Valid conclusion: *post-activation boundary/handoff guidance did not
  reliably redirect the request.* Invalid conclusion: *the router incorrectly
  selected code-review.* Whether the router would actually select code-review for
  this request is untested.
- Cases 1, 2, 4 are non_discriminating: a strong base model already performed the
  defect discovery. This is the expected pattern, not a skill failure.

## Method takeaway (preserved as hypothesis, not proof)

- Strong base models may already perform obvious defect discovery well;
  specialized skills may add marginal value in boundaries (merge/approve
  authority, read-only discipline) and routing. This is an observed pattern from
  a single flawed pilot, not a proven law.
- Contamination lesson: an earlier pass reused directories containing a stale
  `result.md`; a worker read it and "matched" the prior answer. The corrected
  protocol mandates fresh directories and raw-evidence retention.

## Required rerun conditions before any `valid` claim

1. Frozen committed fixture for case 5 (real git repo, branch + prior review) with
   `content_hash`.
2. Sanitized deterministic Git env (isolated HOME, controlled `.gitconfig`,
   fixture-specific identity) — no host global identity leak.
3. Routing cases run via real harness selection (no injection) with selected-skill
   captured; execution cases run with deliberate activation.
4. ≥3 independent repetitions per condition; fresh workers; equivalent settings.
