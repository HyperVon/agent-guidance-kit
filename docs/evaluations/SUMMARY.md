# Skill evaluation summary

> **Status: case sets designed; methodology corrected; evaluation *infrastructure*
> is proven end-to-end on the code-review pilot, with frozen fixtures available for
> four pilot skills (Docker execution layer + portable
> catalog-discriminability layer). No *full published efficacy* run (n≥3, graded assertions,
> committed result file) exists yet, and harness-integrated routing (Layer C) is
> still blocked where the harness cannot expose the selected skill.**

This repository has evaluation case sets for every one of the 26 skills at
`skills/<name>/evals/evals.json` (130 cases total), following the schema in
`skills/skill-evaluation/references/evaluation-artifacts.md`.

## Current development protocol

The normal loop is harness-neutral: static validation, a cheap smoke when
needed, candidate-vs-reference regression at n=1 for routine edits, and a
target-vs-baseline qualification at n=1 when marginal value is the question.
Strict target/baseline/placebo n≥3 confirmation remains available only by
explicit choice. The canonical JSON protocol is documented in
`docs/evaluations/protocol-spec.md` and the adapter boundary in
`docs/evaluations/harness-adapter.md`; Docker/Kilo fields in the historical
sections below describe one optional legacy adapter, not a repository-wide
requirement.

Baseline fairness is enforced by assertion scope. `shared-outcome` and
`universal-safety` assertions form the qualification denominator;
`skill-contract` assertions are reported separately and cannot lower the
no-skill baseline's marginal-value score.

## Methodology correction (this change)

An earlier methodology force-injected the target `SKILL.md` into the `target`
worker for **every** case — including routing/neighboring cases. That can
measure post-activation behavior but **cannot establish routing quality**, and
it contradicted `skills/skill-evaluation/SKILL.md` (condition labels in prompts,
a baseline told its guidance was absent, OS isolation described as optional).
The methodology has been corrected and is documented in:

- `docs/evaluations/RUNBOOK.md` — routing vs execution split, corrected
  isolation, evidence retention, fixture policy, repeats/placebo, status
  taxonomy, cleanup-after-evidence, routing-experiment semantics, authorization
  semantics.
- `docs/evaluations/routing-experiments.md` — the three experiment types
  (availability / description-regression / execution-efficacy) and how the
  routing projection is generated per condition.
- `docs/evaluations/result-schema.md` — the machine-readable `result-json`
  block the validator enforces (identity, runtime, protocol, per-case verdict,
  assertion evidence, protocol-validity gates).
- `skills/skill-evaluation/references/evaluation-artifacts.md` — split case
  schema: `routing` and `execution` oracles, `routing_context` (replaces
  `requires_catalog`), and generator `source_hash`/`output_hash`.

## What exists now

- **26 case sets**, 130 per-skill cases: 2 matching, 1 neighboring, 1 ambiguous,
  1 edge per skill. Each case carries `evaluation_modes` (routing/execution) with a
  split oracle: `routing` (graded from harness-selection evidence) and `execution`
  (`expected_output` + `assertions`). Routing cases declare `routing_context`
  (which replaces the old `requires_catalog`); the catalog is **generated**, not
  committed inside the task fixture. A `fixture` block records status (`ready`
  once a frozen fixture exists, else `designed_only`).
- **4 confusion-set families** in `evaluations/confusion-sets/` with 59 shared
  cross-skill discriminator cases (hard-negative, misleading-keyword,
  counterfactual pairs, multi-intent, ambiguous-natural, workflow-transition).
  Each confusion set lists its candidate `skills`; every case prompt avoids naming
  the expected skill. These are the difficult cases that measure catalog
  discriminability (Layer A).
- **1 holdout set** in `evaluations/holdout/` with 4 generalization cases stored
  outside skill directories so ordinary editing does not consume them. Holdout
  results are reported separately from development-case performance.
- Each per-skill case carries a `case_type` classifying its design intent (default
  `smoke` for legacy packs); the discriminator-family cases live in the confusion
  sets.
- **Frozen fixtures exist for 4/26 skills** (the four pilot skills: code-review,
  git-github-workflow, review-feedback-resolution, security-review) — 20
  committed/generator fixtures under `skills/<skill>/evals/files/case-N/` with
  recorded `content_hash`. The remaining 22 skills are `designed_only` (cases
  defined, fixtures not yet frozen).
- Four result files from the earlier exploratory pilots, **reclassified as
  `protocol_status: invalid` / `decision: exploratory`** and preserved as
  historical evidence only:
  - `results/code-review.md`
  - `results/git-github-workflow.md` (case 2 marked **contaminated** by a host
    Git-identity leak — invalid, not a skill win)
  - `results/review-feedback-resolution.md`
  - `results/security-review.md`

## What has NOT been done (and must not be claimed)

- **No full published efficacy run exists yet.** The 4 pilots' infrastructure is
  proven (see below), but the historical result files remain `protocol_status:
  invalid` / `decision: exploratory` and have not been replaced by graded,
  committed runs with quoted evidence.
- **No harness-integrated routing (Layer C) evaluation exists.** All routing to
  date   is Layer A catalog-discriminability (portable model-as-classifier proxy). Where the harness
  cannot expose the selected skill as evidence, Layer C (harness-routing) is `not_run`.
- **Fixtures frozen for only 4/26 skills** (the pilots). The other 22 remain
  `designed_only`; their cases are not executable until fixtures are frozen.
- **No repetitions / placebo yet** for a published efficacy claim. Each smoke was a
  single run; n≥3 repeats and an irrelevant-guidance placebo are still required
  before any efficacy conclusion.
- **No OS-level isolation on the host** — that is why Layer B runs in Docker
  (`Dockerfile.eval` → `kilo-eval:local`), not on the macOS host. Host runs would
  still have to be labeled `protocol_status: limited`.

## Phase 1 reassessment (2026-08-16)

The corrected pipeline was exercised against the four pilot skills
(`code-review`, `git-github-workflow`, `review-feedback-resolution`,
`security-review`) in this CLI environment. Full write-up:
`docs/evaluations/phase1-environment.md`.

- **What ran green:** `hash_fixtures.py` (idempotent; 6 generator fixtures re-hash
  under the full git-state algorithm), `build_routing_catalog.py` (target-present =
  26 skills; each `--target-absent <skill>` = 25, dropping only the named target),
  `validate_evaluations.py` (0 errors / 0 warnings), and `test_validate_evaluations.py`
  (29 tests pass).
- **What could NOT run at the time (host-only):** a protocol-valid run *on the
  macOS host* — Kilo/CLI on a laptop is the harness itself, so it cannot capture
  routing selection as harness evidence, and it cannot create independent OS-contained
  worker contexts (no container; host `~/.gitconfig` leaks the evaluator's personal
  `user.name` / `user.email`; a live `gh` token is present). Per `RUNBOOK.md` §3/§5
  host runs were recorded `not_run` (blocked). **This constraint is now bypassed for
  Layer B by running the workers inside Docker** (see follow-up below).
- **No evidence invented; no historical pilot reused.** The four exploratory pilots
  stay `protocol_status: invalid`.
- **Gate enforcement proven:** a temporary result claiming `valid` + `both_pass` with
  `instruction-only` isolation was rejected by `validate_evaluations.py` (then removed).
  This confirms the pipeline blocks the weakening the rules forbid.
- **Repeats:** 0 at the time. **Protocol status:** `not_run` for host runs.

> The next two dated sections are historical records. Their paths and command
> descriptions reflect the runner and commit being reported at that time; the
> current protocol is documented in **Current integrity follow-up (2026-08-20)**
> below.

## Infrastructure proven (2026-08-16, follow-up)

The corrected pipeline was taken past "schema green" to a working three-layer
runner, proven on the `code-review` pilot (fixtures already frozen for all 4
pilots):

- **Layer A — catalog-discriminability (portable, harness-independent). `scripts/run_catalog_routing_eval.py`
  issues a fresh model call per repetition over a generated neutral catalog and
  captures a structured `{"selected_skill": ...}` decision. Smoke on case 1:
  target-present selected `code-review` 3/3; target-absent returned `null`/clarify
  (real behavior; the catalog otherwise had no plain code-review owner).
- **Layer B — Docker execution-efficacy.** `Dockerfile.eval` builds `kilo-eval:local`
  (Node 22, `@kilocode/cli`, deterministic eval git identity, **no** host
  `~/.gitconfig`/`~/.ssh`/tokens, **no** mounted Kilo auth). `scripts/run_execution_eval.py`
   runs fresh containers: the `target` condition mounts *guidance only*
   (`SKILL.md` + `references/`, never the `evals/` fixture snapshot) at
   /work/guidance/task; baseline mounts **nothing**. Smoke on case 5
   (n=1, infrastructure only): two **distinct fresh containers** confirmed; both
   started from the identical frozen seed (starting fixture hashes matched the
   frozen `output_hash`); target and baseline outputs captured. This is an
   **infrastructure smoke, not an efficacy claim** (n≥3 + an irrelevant-guidance
   placebo are still required before any efficacy conclusion).
  - **Boundary probe green.** `scripts/docker_isolation_preflight.py` passes all 23
    checks (isolated home, deterministic git identity, no ssh/token/host-config host
    path leak, no Kilo auth mount, **target-skill guidance absent in baseline AND present,
    readable, hash-matched, with references in the target mount** at the real
   `/work/guidance/task/SKILL.md` path).
 - **Model access is anonymous + free + pinned (cost gate, not a methodology rule).** The
   model `kilo/tencent/hy3:free` is reached through Kilo Gateway with no API key mounted;
   absence of `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` does **not** mean no provider. The model
   is **pinned** (not auto-routed) so target and baseline conditions share identical
   inference; `--auto` is only permission auto-approval. The free-model restriction is a
   **cost-safety gate** (`require_free_model` refuses a non-`:free` model unless
   `--allow-paid-model`); a paid model is methodologically valid if all conditions use the
   identical resolved model. The free-model catalog changes over time — update
   `DEFAULT_MODEL` in the runners when it is retired. The **Kilo CLI version is pinned** in
   `Dockerfile.eval` (`ARG KILO_CLI_VERSION`) and recorded in the evidence.
 - **Runner hardening (shared-fixture / contamination fixes).** Each repetition now uses
   **two independent copies of one pristine seed** (`/work/task` per condition) so the
   target worker can never mutate the baseline's state; both starting hashes are recorded
   and must match. Generator source (`setup.sh` / answer key) is run in a sanitized
   environment and **stripped** from the worker seed. A failed Docker/Kilo run is recorded
   `run_status="failed"` and the validator **rejects** the evidence. `--check-evidence`
   dispatches on an explicit `evidence_type` field, so unknown/malformed evidence is a hard
   error, never silently skipped. Catalog-routing distinguishes a *failed model invocation*
   from a *valid null-selection* (`status` vs `decision`), so a model failure can no longer
   masquerade as a "clarify / target-absent" pass.

These prove the *infrastructure* is sound. What remains before any published
efficacy claim: n≥3 repetitions per condition, an irrelevant-guidance placebo,
frozen-assertion grading with quoted evidence, and committed result files.

## Current-head rerun (2026-08-17)

The runner hardening in `fix/evaluation-runner-integrity` (PR #47) was
**re-run end-to-end on the current head** after the macOS `/tmp` mount fix and
the corrected fixture/guidance hash semantics. Exact results:

- **HEAD:** `2e963364cec45a35b75d6c4253c9e7c326170b15` (branch
  `fix/evaluation-runner-integrity`, PR #47).
- **`docker build -f Dockerfile.eval -t kilo-eval:local .`** — succeeded
  (`Successfully tagged kilo-eval:local`).
- **`docker_isolation_preflight.py --image kilo-eval:local --target-skill
   code-review`** — **23/23 checks passed**. The target mount now additionally
  proves `references_present_if_required` (a required `references/` directory
  that is missing now FAILS the probe; previously this check could not fail).
- **Catalog-routing smoke** (`run_catalog_routing_eval.py --skill code-review
  --case-id 1 --reps 3`): `target_present` selected `code-review`/**apply**
  3/3; `target_absent` returned `null`/**clarify** 3/3. Hardening proven: a
  decision that *omits* `selected_skill` or `action` is now rejected (it can no
  longer become an explicit `null` selection), and a non-null selection that is
  not present in the catalog actually supplied to the model (e.g. a target
  selected under a target-absent catalog) is rejected.
- **Execution smoke** (`run_execution_eval.py --skill code-review --case-id 5
   --reps 1`): two **distinct fresh containers**; target and baseline both
  started from the identical **frozen** seed — `canonical_seed_hash`
  (`sha256:694cc87e…`) equals the frozen fixture `output_hash`/`content_hash`.
  `guidance_bundle_hash` was recorded and is now required by the validator.
  **n=1 infrastructure smoke — not an efficacy claim.**
- **`validate_evaluations.py --check-evidence`** — **PASSED** on the actual
  current-head smoke files (no errors / no warnings).
- **`validate_evaluations.py`** (schema) — 0 errors / 0 warnings.
- **`test_validate_evaluations.py`** — **75 tests pass** (up from 50; 25 new
  regression tests covering the routing missing-field/catalog-membership
  defects, the generator source-vs-output hash split, the frozen-hash anchor,
  the references probe, and the Kilo-path/mode consistency fixes).
- **`hash_fixtures.py`** — idempotent; the 6 generator fixtures re-hashed under
  the corrected semantics (worker-visible `output_hash`/`content_hash`, with
  `setup.sh` **excluded**; `source_hash` still covers `setup.sh`). Second run:
  `Updated 0`.

### Generator hash semantics corrected

`materialize_fixture_seed` is now the single canonical worker-visible
materialization. `canonical_hash` and `verify_generator_deterministic` both defer
to it, so the frozen `output_hash`/`content_hash` always describe exactly the
artifact the worker receives:

- `source_hash` = hash of the evaluator-only generator source (`setup.sh`);
- `output_hash` / `content_hash` = hash of the **worker-visible** generated task
  state (generator source stripped before hashing).

This closes the gap where the frozen hash and the task actually presented to the
worker were different artifacts.

### Catalog-routing integrity

`extract_decision` now validates the **raw** model JSON: both `selected_skill`
and `action` must be explicitly present (a missing field is NOT an explicit
`null`), unknown actions are rejected, and a non-null `selected_skill` must name
a skill that was actually in the catalog supplied for that condition. The
frozen-hash anchor plus the guidance-bundle hash mean a malformed, stale,
partially-mounted, or differently-materialized evaluation cannot masquerade as
trustworthy evidence.

## Current integrity follow-up (2026-08-20)

This section records only checks performed against the current working head; it
does not rewrite the historical smoke reports above and does not claim a model
execution result.

- The deterministic validator passed with 26 skills, 0 hard errors, and 0
  warnings. `test_validate_evaluations.py` passed with **173 tests** and 4
  subtests; `ruff check scripts/`, Python compilation, the README catalog-index
  check, `git diff --check`, and `hash_fixtures.py` (`Updated 0 evals.json
  files`) also passed.
- The current runner uses `/work/task`, places target/placebo guidance under
  `.kilo/skills/<name>/`, activates both through `--command <name>:skill`, and
  gives baseline no treatment tree or command. The validator now anchors each
  `natural_task_hash` to the current source case prompt and requires the exact
  canonical runtime-treatment path list.
- The host Kilo CLI reports version `7.4.22`; the local pinned binary contains
  the `$ARGUMENTS` and positional placeholder forms that the runner now rejects
  before worker launch. No canonical skill file is rewritten.
- A current target/baseline/placebo Docker smoke was **not run**: Docker and
  the isolation preflight stopped before worker launch because the Colima
  Docker socket was unavailable (`~/.colima/default/docker.sock`).
  Therefore this follow-up contains no new target, baseline, placebo, or
  efficacy result claim.

## Layer A completed + routing-description fixes (2026-08-22)

All four confusion sets are now complete at 3 reps each (development evidence only;
Layer A is a catalog-discriminability proxy, not harness-routing evidence):

| Confusion set | Observations | Misroutes (pre-fix) | Misroutes (post-fix) |
| --- | ---: | ---: | ---: |
| review-family | 48 | 6 | 0 |
| design-change-family | 51 | 3 | 3 |
| investigation-family | 45 | 6 | 6 |
| skill-maintenance-family | 50 | 3 | 3 |

- **`code-review` → `security-review` (one-directional) fixed.** Pre-fix, all
  3 errors were expected-`code-review` observations selecting `security-review`
  on change-set reviews that touched auth/token code; no case ever intended
  `security-review`. Post-fix: `code-review` 6/6, `security-review` over-selection gone.
- **`architecture-review` over-clarify fixed.** Pre-fix it returned explicit null on
  3 of its own hard-negative observations; post-fix 6/6.
- Description edits were made to exactly three frontmatter descriptions
  (`code-review`, `security-review`, `architecture-review`) based only on these
  development results, then revalidated against all four sets.
- **No new neighbor regressions:** every intended-skill observation outside the two
  targeted errors was already perfect and stayed perfect. Two unchanged ambiguous-null
  behaviors remain recorded as explicit observations (design-change and
  skill-maintenance ambiguous cases still select a plausible owner instead of
  clarifying; investigation-family's ambiguous case swapped confusion partner from
  `security-review` to `threat-modeling` — still never clarifies). These are
  preserved as-is; they were not tuned against.
- **Holdout generalization:** pre-change holdout baseline (run before any description
  edit): 21/21 observations correct, including all three changed skills. Post-change
  holdout: 21/21 — flat at ceiling, no regression. Holdout cases were not folded into
  development data.
- Raw evidence: `.eval-evidence/layerA-{review,design-change,investigation,
  skill-maintenance}-family{,-postfix}.json`, `.eval-evidence/holdout-review-discrim-1-{prechange,postchange}.json`
  (gitignored). Undefined precision/recall values are recorded as null wherever a
  denominator is zero (e.g., `security-review` in review-family has no
  intended-`security-review` observations).
- Layer C harness-routing remains `not_run`: none of this is evidence about real
  harness selection.

## Qualification rerun batch (2026-08-22, post-runner-fix)

The three qualification pilots were re-run after commit `c48961b` fixed the seed-copy
workspace-root permission bug (a non-owner container uid could not enumerate a ~0733
workspace root) and made permission-normalization failures fail closed. Each rerun used the
same protocol class (`qualification`, target/baseline, n=1, fresh independent workers,
Docker strict isolation, fresh-context blind grading over randomized A/B labels); the
original result files are preserved unchanged as pre-fix historical records.

- `security-review` case 1 — the current-head measurement is
  **non-discriminating (`both_fail`)**: target 3/4, baseline 2/4
  ([rerun 2](results/security-review-qualification-n1-rerun2.md)). The target sample
  failed the frozen read-and-redact assertion by quoting the fixture's literal bearer
  tokens verbatim; the baseline kept credentials location-only. Two earlier n=1
  comparisons of the same case (pre-fix runner, and post-fix pre-description-edit, raw
  evidence archived) were both `skill_only_pass` (4/4 vs 3/4). The three n=1 samples
  disagree on direction; none is an efficacy claim, and the disagreement is exactly what
  placebo + n≥3 confirmation must resolve before any claim.
- `review-feedback-resolution` case 1 — target 4/4, baseline 2/4
  ([rerun](results/review-feedback-resolution-qualification-n1-rerun1.md)); direction
  unchanged, margin narrowed (this baseline sample recorded context and grounded its
  declines but still failed the disposition taxonomy).
- `git-github-workflow` case 1 — target 4/4, baseline 3/4
  ([rerun](results/git-github-workflow-qualification-n1-rerun1.md)); direction unchanged,
  margin narrowed (baseline again committed through the unrunnable verification gate).

All three remain single-repetition pilot observations, **not** efficacy claims. The two
discriminating skills agree in direction across their original and rerun comparisons;
`security-review`'s three samples disagree (see above), and every run is still
qualification n=1.

**Evidence retention status:** every committed result binds its case to a SHA-256
`raw_evidence_hash` over the canonical file in the ignored `.eval-evidence/` directory, but
those raw files still live only on the evaluation host's disk. Durable independent
verification (sanitized content-addressed evidence bundles, CI artifacts, or release assets)
remains a **follow-up**: it needs a sanitization pass that strips personal paths and
environment metadata before anything is published, which is larger than this change set.

## Qualification batch (2026-08-22)

First evaluation batch on a native Linux Docker host, after fixing the runner's
seed-copy permission handling for uid-mapped container runtimes (PR #56: directory
traverse bits, a+rwX normalization, `0700` staging directory — found by the
mandatory fresh-context adversarial review of the portability fix).

- **Smoke re-proven** end-to-end (`code-review` case 5): target and baseline both
  succeeded in distinct containers/sessions from one hash-verified seed; target
  guidance probe and context probe present, baseline probe absent;
  `--check-evidence` passed.
- **Three protocol-valid qualification runs** (Docker, target/baseline, n=1,
  fresh-context blind grading over randomized labels), each recorded in a
  committed result file with the full v3 `result-json` schema:
  - `security-review` case 1 — target 4/4, baseline 3/4
    ([results](results/security-review-qualification-n1.md));
  - `review-feedback-resolution` case 1 — target 4/4, baseline 0/4
    ([results](results/review-feedback-resolution-qualification-n1.md));
  - `git-github-workflow` case 1 — target 4/4, baseline 2/4; the baseline
    committed through a red/skipped verification gate while the target treated
    the gate as a blocker
    ([results](results/git-github-workflow-qualification-n1.md)).
  These are single-repetition pilot observations, **not** efficacy claims.
- **Layer A started:** `review-family` confusion set complete (15 cases, 48
  observations at 3 reps, free model): a one-directional boundary misroute —
  all 3 errors are expected-`code-review` observations selecting
  `security-review` (`security-review` precision 0.0, recall undefined on this
  set) — and `architecture-review` over-clarifying (3 explicit-null selections,
  recall 0.5). The other three confusion sets and the holdout remain unrun.
- Execution validated 4/26; measurement at the current measurement points:
  discriminating 2/26, non-discriminating 2/26 (all n=1 pilots except
  code-review n=3); routing (Layer C) still `not_run` everywhere.

## Case-set audit

All 130 cases were audited against their `SKILL.md`. The main structural change in
this pass is the **routing/execution oracle split**: every routing case now carries
a `routing` expectation graded from harness-selection evidence (not worker prose),
and every execution case keeps `expected_output` + `assertions`. The old single
shared `expected_output`/`assertions` block no longer serves both modes; routing-only
cases no longer carry handoff-prose assertions.

Authorization-semantics bugs found and fixed (prompt already granted the action,
but the oracle wrongly framed it as missing authorization — distinguishing "missing
authorization" from "invalid scope" and "another workflow owns the action"):

- `skill-authoring` case 5 — the prompt explicitly asks to commit and publish.
  Corrected: reject the unbounded "tidy all other skills" scope expansion, keep to
  the approved code-review change, and route commit/publish through
  `git-github-workflow` once a validated change set exists; do **not** claim the
  user failed to ask, and do **not** publish an unbounded/invalid set just because
  publication was requested.
- `documentation-review` case 5 — the prompt explicitly asks to apply fixes and open
  a PR. Corrected: the skill is report-first for doc-vs-truth accuracy; operational
  runbook edits and the PR belong to the implementation / `git-github-workflow`
  workflows, so it routes those rather than claiming authorization was missing.

Earlier oracle bugs preserved from the prior pass:

- `architecture-review` case 5 — the prompt *is* the later explicit implementation
  request; expected behavior was wrongly "refuse because implementation wasn't
  authorized." Corrected to: review is complete, exit pure-review mode, hand off to
  the implementation workflow, preserve the approved decision, do not claim the
  rewrite is inside architecture-review.
- `frontend-quality-review` case 5 — the prompt explicitly authorizes the fixes and
  screenshots; expected behavior wrongly demanded refusal. Corrected to: acknowledge
  authorization, exit pure-review mode, route/use the appropriate
  implementation/browser-capable workflow, do not claim authorization is missing.

No skill was rewritten merely to make an eval pass. Remaining limitations: the
audit preserved faithful oracles but did not re-run anything; corrected oracles
need execution runs to produce evidence.

## How evaluations are run (corrected)

`docs/evaluations/RUNBOOK.md` is the authoritative method. Key points: separate
routing (real harness selection, capture selected skill) from execution
(deliberate activation vs harness default); keep conditions independent and
leak-free with neutral names and no condition labels; freeze reproducible
fixtures with `content_hash`; retain raw evidence in an ignored dir; grade with
quoted evidence; record the full result schema; prefer ≥3 repetitions for any
efficacy claim; do not compare raw "X/5" across skills as a quality score.

## Next step

The four pilot skills' fixtures are now frozen (20 committed/generator fixtures
with `content_hash`). The next step is to **rerun those four pilots under the
corrected protocol** — routing via real harness selection (capture selected
skill; mark `limited`/`not_run` if the harness cannot expose it), execution via
deliberate activation vs harness default, with a sanitized deterministic Git
environment (isolated `HOME`, controlled `.gitconfig`, fixture-local identity —
no host global identity leak), an optional irrelevant-guidance placebo, and ≥3
independent repetitions per condition. The corrected runs must be recorded with
the full result schema and raw evidence retained in `.eval-evidence/`. Until
then those four remain `protocol_status: invalid` / `exploratory`. The remaining
22 skills are still `designed_only` / `not_run` and need frozen fixtures before
they can be executed; everything remains pending a proper harness capability or
OS sandbox.
