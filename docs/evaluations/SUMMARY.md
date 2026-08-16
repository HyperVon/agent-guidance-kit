# Skill evaluation summary

> **Status: case sets designed; methodology corrected; no protocol-valid runs
> exist yet.**

This repository has evaluation case sets for every one of the 26 skills at
`skills/<name>/evals/evals.json` (130 cases total), following the schema in
`skills/skill-evaluation/references/evaluation-artifacts.md`.

## Methodology correction (this change)

An earlier methodology force-injected the target `SKILL.md` into the WITH-SKILL
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

- **26 case sets**, 130 cases: 2 matching, 1 neighboring, 1 ambiguous, 1 edge.
- Each case now carries `evaluation_modes` (routing/execution) with a split
  oracle: `routing` (graded from harness-selection evidence) and `execution`
  (`expected_output` + `assertions`). Routing cases declare `routing_context`
  (which replaces the old `requires_catalog`); the catalog is **generated**, not
  committed inside the task fixture. A `fixture` block records status
  (`ready` once a frozen fixture exists, else `designed_only`).
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

- **No routing evaluation exists.** All prior runs force-injected the target
  skill, so harness routing was never measured. Routing cells in the matrix are
  `not_run`.
- **No protocol-valid execution run exists.** The four pilots are `invalid`
  (force-injection + instruction-only containment + condition-labeled prompts).
  They are historical/exploratory, not validated proof.
- **Fixtures frozen for only 4/26 skills** (the pilots). The other 22 remain
  `designed_only`; their cases are not executable until fixtures are frozen.
- **No repetitions / placebo.** Each pilot was a single run; no n≥3 repeats, no
  irrelevant-guidance placebo.
- **No OS-level isolation** was available in this CLI; runs here must be labeled
  `protocol_status: limited` even when rerun.

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
