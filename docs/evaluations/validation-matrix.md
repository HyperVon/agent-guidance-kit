# Evaluation validation matrix

Status dimensions are kept separate (per the corrected methodology):

- **Fixtures** — `ready` (frozen committed fixture with `content_hash`) vs
  `designed_only` (case defined, not yet executable).
- **Routing** — does a *harness-selection* run exist? (real router, captured
  selected skill). `not_run` unless measured that way. Catalog-discriminability
  (Layer A) is a portable model-as-classifier proxy, not a harness-routing
  measurement — see the confusion-set matrix, not the per-skill routing column.
- **Execution** — does a *post-activation* run exist? `exploratory` (force-injected,
  instruction-only, historical) vs `pending` vs `valid`.
- **Measurement** — did the valid run discriminate? `not_run` (no valid run), `✓ discriminating` (target beats controls), `? non_discriminating` (all pass/fail equally), `? inconclusive` (mixed/unreliable), `⚠ baseline-favored`, `invalid` (no valid measurement). Protocol-valid execution is **not** a measurement win.
- **Protocol** — `valid` / `limited` / `invalid` / `not_run`.
- **Repeats** — number of independent repetitions per condition (pilot = 1).
- **Result** — link to the per-skill result file.

New development runs are harness-neutral and declare one of the explicit
protocols: `smoke` (target only, n=1), `qualification` (target/baseline, n=1),
`regression` (candidate/reference, n=1), or `confirmation`
(target/baseline/placebo, n≥3). A harness adapter may use Docker, a local
sandbox, a VM, or an agent CLI; the matrix records the adapter name only when a
run exists. The historical Kilo/Docker row below is an optional strict adapter
record, not the default harness for the repository.

> **Important:** The four original pilot result files (`results/code-review.md`,
> `results/git-github-workflow.md`, `results/review-feedback-resolution.md`,
> `results/security-review.md`) contain only `protocol_status: invalid` /
> `decision: exploratory` historical pilots and do **not** constitute validated
> evidence; they are not the records linked from the table rows below. No
> harness-routing (Layer C) result exists for any skill yet (historical runs were
> force-injected, so routing is unmeasured). No cross-skill "X/5"
> comparison is a skill-quality score.
>
> **Phase 1 reassessment (2026-08-16) + follow-up:** the corrected pipeline was
> exercised in this CLI environment. The fixture/hashing/catalog/validation half
> runs green (fixtures idempotent, catalogs generate for both conditions, validator
> + 29 tests pass). A protocol-valid run on the **macOS host** is still not possible
> (Kilo/CLI on a laptop is the harness itself: it cannot capture routing selection as
> harness evidence, and cannot create independent OS-contained worker contexts — host
> `gitconfig`/`gh` token present). **However, Layer B (execution) now runs inside
> Docker** (`Dockerfile.eval` → `kilo-eval:local`: fresh containers, deterministic
> git identity, no host secrets, no mounted auth, anonymous free model
> `kilo/tencent/hy3:free`), and **Layer A (catalog-discriminability) is fully portable** and
> runs on the host. Both were smoke-proven on the `code-review` pilot (distinct
> container IDs; target applied the skill vs baseline refusal; catalog-
> selected the target when present and declined when absent). **Layer C
> (harness-routing) stays `not_run`** where the harness cannot expose the selected
> skill. Net: for the four pilot skills **execution infra = proven**,
> **catalog-discriminability = proven**, **harness-routing = `not_run` (blocked)**,
> protocol `not_run` (no graded n≥3 run published yet), repeats 0. The historical
> exploratory pilots remain `invalid` and were not reused.
>
> **Update 2026-08-20:** `code-review` now has a protocol-valid Tier-2 execution run (Docker, n=3) at `results/code-review-first-valid.md` — execution `valid`, protocol `valid`, measurement non-discriminating on the frozen design (see result for routing catalog analysis and placebo gap).
>
> **Update 2026-08-22:** first Linux-host evaluation batch, after the runner portability fix
> (PR #56: seed-copy directory traverse bits, a+rwX normalization, `0700` staging dir). Smoke
> re-proven end-to-end (`code-review` case 5). Three protocol-valid qualification runs (Docker,
> target/baseline, n=1, fresh-context blind grading): `security-review` case 1 target 4/4 vs
> baseline 3/4 ([results](results/security-review-qualification-n1.md)); `review-feedback-resolution`
> case 1 target 4/4 vs baseline 0/4 ([results](results/review-feedback-resolution-qualification-n1.md));
> `git-github-workflow` case 1 target 4/4 vs baseline 2/4 — the baseline committed through a
> red/skipped verification gate
> ([results](results/git-github-workflow-qualification-n1.md)). All three are single-repetition
> pilot observations, not efficacy claims. Layer A catalog-discriminability started:
> `review-family` confusion set complete (15 cases, 48 observations at 3 reps) —
> one-directional capture at the security boundary (all 3 misroutes are
> expected-`code-review` observations selected as `security-review`;
> `security-review` precision 0.0, recall undefined on this set) and
> `architecture-review` over-clarifying
> (3 explicit-null selections, recall 0.5). The other three confusion sets and the holdout
> remain unrun. The historical exploratory pilots stay in their original result files
> (linked from SUMMARY), not in the rows below.

**Default harness:** none — use an explicitly recorded adapter.  **Historical
strict adapter:** Kilo/CLI through Docker (`isolation_method: docker`); host-only
runs are still instruction-only and must be labeled `limited`.

| Skill | Cases | Fixtures | Routing | Execution | Measurement | Protocol | Repeats | Result |
| :--- | :---: | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| [adversarial-pr-review](../../skills/adversarial-pr-review/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [ai-slop-detector](../../skills/ai-slop-detector/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [architecture-review](../../skills/architecture-review/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [code-review](../../skills/code-review/evals/evals.json) | 5 | ready (5/5) | not_run | valid | ? non_discriminating | valid | 3 | [results](results/code-review-first-valid.md) |
| [codebase-orientation](../../skills/codebase-orientation/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [dependency-upgrade](../../skills/dependency-upgrade/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [documentation-review](../../skills/documentation-review/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [frontend-quality-review](../../skills/frontend-quality-review/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [git-github-workflow](../../skills/git-github-workflow/evals/evals.json) | 5 | ready (5/5) | not_run | valid | ✓ discriminating | valid | 1 | [results](results/git-github-workflow-qualification-n1-rerun1.md) |
| [harness-adaptation](../../skills/harness-adaptation/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [implementation-planning](../../skills/implementation-planning/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [parallel-multi-agent](../../skills/parallel-multi-agent/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [quality-hardening](../../skills/quality-hardening/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [reduce-code-size](../../skills/reduce-code-size/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [repository-guidance-authoring](../../skills/repository-guidance-authoring/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [requirements-and-design](../../skills/requirements-and-design/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [review-feedback-resolution](../../skills/review-feedback-resolution/evals/evals.json) | 5 | ready (5/5) | not_run | valid | ✓ discriminating | valid | 1 | [results](results/review-feedback-resolution-qualification-n1-rerun1.md) |
| [rules-and-skills-audit](../../skills/rules-and-skills-audit/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [security-review](../../skills/security-review/evals/evals.json) | 5 | ready (5/5) | not_run | valid | ? non_discriminating | valid | 1 | [results](results/security-review-qualification-n1-rerun2.md) |
| [skill-authoring](../../skills/skill-authoring/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [skill-discovery](../../skills/skill-discovery/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [skill-evaluation](../../skills/skill-evaluation/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [skill-optimizer](../../skills/skill-optimizer/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [skill-reviewer](../../skills/skill-reviewer/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [systematic-debugging](../../skills/systematic-debugging/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |
| [threat-modeling](../../skills/threat-modeling/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | not_run | – | – |

Total: 26 skills, 130 designed cases. Fixtures frozen for 4/26 (the four pilot
skills: code-review, git-github-workflow, review-feedback-resolution,
security-review). Routing (Layer C) measured for 0/26. Execution validated for 4/26
(code-review confirmation n=3 at `results/code-review-first-valid.md`;
review-feedback-resolution / git-github-workflow qualification n=1 reruns;
security-review qualification n=1 rerun 2). Measurement discriminating: 2/26 (n=1
pilot observations); Measurement non-discriminating: 2/26 (`code-review` n=3;
`security-review` current-head rerun 2 — see its three-measurement history).

### Historical Phase 1 state — 2026-08-16
Layer A catalog-discriminability and Layer B Docker execution **infrastructure proven** (single-rep smoke on `code-review`;
distinct containers, independent seed copies, baseline received no guidance, free
anonymous model reachable, runner failure correctly rejected). Layer C harness-routing
`not_run` (blocked — no harness selection capture in this CLI). Execution evidence is
validated by `validate_evaluations.py --check-evidence`, which dispatches on an explicit
`evidence_type` field and rejects unknown/malformed evidence rather than skipping it.
No graded n≥3 run published yet, so protocol stayed `not_run`. The validator rejects
inflated `valid` claims (verified by negative test).

### Current state — 2026-08-20
`code-review` now has a protocol-valid Tier-2 execution result at `results/code-review-first-valid.md` (n=3, execution `valid`, protocol `valid`, measurement `? non_discriminating`). `code-review` applied all three P1 findings in 3/3 reps but merged/self-approved in 1/3 (baseline 3/3, placebo 0/3). Execution validated 1/26, Measurement non-discriminating 1/26. Full efficacy runs require a graded n≥3 comparison with quoted evidence; see `phase1-environment.md` §6.

## Current state — 2026-08-22 (Layer A complete + routing-description fixes)

> **Superseded snapshot:** superseded by the v4 section below (descriptions were
> subsequently shortened to router-facing metadata and all sets re-run with full
> attempted/successful/failed accounting).

All four Layer A confusion sets are complete (3 reps, 194 development observations).
Development-evidence description fixes to `code-review`, `security-review`, and
`architecture-review` removed all 6 review-family misroutes (code-review→security-review
one-directional capture; architecture-review over-clarify) with no new neighbor
regressions. Holdout: pre-change baseline 21/21 and post-change 21/21 — generalization
held at ceiling; holdout cases were not folded into development data. Layer C remains
`not_run` (catalog discriminability is a proxy, not harness routing). Ambiguous-null
capture behavior in design-change/investigation/skill-maintenance sets is recorded as an
explicit observation, untuned. Execution rows: 4/26 validated; at the current measurement
points 2/26 discriminating and 2/26 non-discriminating (see below).

## Current state — 2026-08-22 (Layer A v4: short router-facing descriptions)

Frontmatter descriptions are routing metadata for the LLM router, not documentation. The
three touched descriptions were rewritten as compact discriminators (`code-review`
105→45 words, `security-review` 112→44, `architecture-review` 54→34), two development
cases (#16 subsystem review, #17 bounded-repo review) protect `code-review`'s non-diff
scope, and every set now records `attempted_decisions` / `successful_decisions` /
`failed_decisions` so failed invocations stay visible:

| Set | Attempted | Successful | Failed | Intended-skill errors |
| --- | ---: | ---: | ---: | ---: |
| review-family | 54 | 53 | 1 | 1 (case 1 → `security-review`, 2/3) |
| design-change-family | 51 | 51 | 0 | 0 |
| investigation-family | 45 | 45 | 0 | 0 |
| skill-maintenance-family | 51 | 50 | 1 | 0 |

skill-maintenance is reported as **50 successful + 1 failed invocation — not complete**:
its case 7 prompt reliably makes the worker request a permission in the mandated pure/
no-tools mode (CLI auto-rejects, exit 1; failed in all three recorded set attempts).
Ambiguous-null capture persists untuned. Unchanged holdout run once post-shortening:
21/21 attempted, 21/21 successful — flat vs baseline. Layer C remains `not_run`.

## Current state — 2026-08-22 (post-runner-fix reruns)

Commit `c48961b` fixed the seed-copy workspace-root permission bug (non-owner container uid
could not enumerate a ~0733 workspace root; X propagation checked only S_IXUSR; chmod
failures were swallowed) and added a container-side workspace enumeration probe to the
isolation preflight. All three qualification pilots were re-run under the corrected runner
(same protocol class: qualification, target/baseline, n=1, fresh workers, blind randomized
grading). Final current-head outcomes (rows above link these result files; pre-fix files
remain as historical records):

- `git-github-workflow`: 4/4 vs 3/4 — discriminating, margin narrowed.
- `review-feedback-resolution`: 4/4 vs 2/4 — discriminating, margin narrowed.
- `security-review`: an interim post-fix run reproduced 4/4 vs 3/4, but the current-head
  rerun ([rerun 2](results/security-review-qualification-n1-rerun2.md)) measured
  **3/4 vs 2/4, both_fail / non-discriminating** — the target sample quoted fixture token
  literals verbatim. Three n=1 samples for this case disagree on direction; none is an
  efficacy claim.

Layer A then completed all four confusion sets and fixed the two development-evidence
candidates (`code-review` → `security-review`, `architecture-review` over-clarify) with the
holdout flat at ceiling pre/post (21/21 both) — see the Layer A section above. Remaining:
repeats/placebo before any efficacy claim, Layer C still blocked.

## Current state — 2026-08-22

> **Superseded snapshot:** this paragraph records the original PR-#56-era batch only. The
> current measurement points are in the sections above (`security-review` now links its
> non-discriminating rerun 2; totals are 2 discriminating / 2 non-discriminating).

Runner portability fixed for native Linux Docker (PR #56) and the pipeline re-proven end-to-end on this host: smoke (`code-review` case 5) plus three protocol-valid qualification runs, all discriminating at n=1 (security-review 4/4 vs 3/4; review-feedback-resolution 4/4 vs 0/4; git-github-workflow 4/4 vs 2/4 — baseline committed through a red/skipped gate). Rows above link the new result files; the historical exploratory pilots remain preserved under their original names. Layer A `review-family` confusion set is complete (48 observations): a one-directional `code-review` → `security-review` misroute (3 of the 6 expected-`code-review` observations selected `security-review`; no case intends `security-review`) and `architecture-review` over-clarify (3 explicit nulls) are the first concrete description-fix candidates. Remaining: other three confusion sets + holdout (Layer A), repeats/placebo before any efficacy claim, Layer C still blocked.

## Legend

- `designed_only` — case set exists; no reproducible fixture yet.
- `not_run` — no execution/routing run recorded.
- `exploratory` — historical force-injected pilot; `protocol_status: invalid`; not
  validated proof.
- `invalid` — run cannot be scored as valid (method or environment contamination).
- `limited` — weaker fallback (e.g. instruction-only containment) used knowingly.
- `valid` — meets the corrected protocol (OS-contained or verified harness
  routing; frozen fixtures; evidence retained).
- `Measurement` — `✓ discriminating` (target beats controls), `? non_discriminating` (all pass/fail equally), `? inconclusive` (mixed/unreliable), `⚠ baseline-favored`, `not_run`/`invalid` (no valid measurement). Execution `valid` + Measurement `non_discriminating` means a trustworthy experiment that did **not** demonstrate unique skill value — not a contradiction.

## How to run (corrected)

For each skill, follow `skills/skill-evaluation/SKILL.md` and `RUNBOOK.md`:
build frozen fixtures, run **routing** via real harness selection (capture
selected skill) and **execution** via deliberate activation, keep conditions
independent and leak-free, retain raw evidence, grade with quoted evidence, and
record the full result schema. Do not force-inject the target skill for routing
cases. Do not count force-injected runs as routing proof.
