# Skill evaluation runbook

How to actually run the evaluations in this repo, end to end. Written so a future
agent does not have to rediscover the method. Companion to `validation-matrix.md`
and `SUMMARY.md`.

## Philosophy (read first)

- **Tasks must be hard and fair.** If a task is too basic, any decent model passes
  without the skill, and the eval cannot discriminate useful behavior. Build
  realistic, multi-file scenarios with genuine traps.
- **Do not rig.** Never design tasks so only the skill can pass. The traps should
  exercise the skill's *actual* value — its discipline, boundaries, and structure.
  A strong baseline should be *able* to do well; the skill should make the correct
  behavior systematic and reliable. The comparison is only meaningful when the
  baseline could plausibly succeed but the skill changes the outcome.

## Designing discriminating tasks (key lesson)

Strong base models already find defects, so **defect-finding cases rarely
discriminate** — both WITH-SKILL and BASELINE will catch a bad diff. The skill's
marginal value is in **boundaries and discipline**, so build cases around that:

- **Routing/hand-off:** requests that belong to a *neighbor* skill. The skill
  should name the owner and hand off; a baseline tends to answer in-place.
- **Approval/merge boundaries:** give the worker something it *can* act on and ask
  it to "approve and merge." The skill must refuse; record whether the baseline
  does too. Make the fixture a **real git repo with a branch + prior review** so
  the merge is actually possible (otherwise both refuse for the wrong reason and
  the case is non-discriminating).
- **Verification discipline under pressure:** frame a matching case as "the author
  says it's fixed, please verify and approve." Plant a diff that *looks* like a fix
  but only adds logging/comments/defaults. The skill must trace the root cause,
  confirm the diff alters behavior, and refuse to claim readiness; a baseline is
  tempted to approve. This tests the skill's anti-patterns (phantom verification,
  accepting fix claims), which is its real value.
- Keep one or two genuine defect-finding cases for coverage, but expect them to be
  non-discriminating and mark them as such rather than forcing a skill win.

The goal is evidence about *where the skill helps*, not a guaranteed skill victory.
- One comparison = one **WITH-SKILL** worker vs one **BASELINE** worker on the same
  task and fixtures.

## Isolation model

Per `skills/skill-evaluation`, a valid run needs two independent workers whose
contexts do not contain the target skill. This repo uses **directory isolation +
fresh subagents** (no OS jail required, but see hardening below):

- Each case gets a directory **outside the repo** (session temp dir, e.g.
  `/var/folders/.../kilo/eval-runs/<skill>/caseN/<cond>/`). Keeping it off-repo
  avoids accidental catalog contamination.
- `<cond>/with-skill/` contains: `task.md` (the prompt + scenario) and
  `skills/<name>/SKILL.md` (plus its `references/` if present).
- `<cond>/baseline/` contains **only** `task.md` — no skill file, no repo catalog.
- Launch a **fresh subagent** per worker (the `task` tool). Subagents do not
  inherit the parent's context, so the baseline genuinely never sees the skill.
- Instruct each worker to operate *only* inside its directory and to edit nothing.

### Residual caveat (state it in results)
Isolation is **by instruction, not OS-enforced**. A worker could in principle
traverse to the catalog; nothing prevents it. An in-container agent runner
(Docker) would enforce the boundary — that is optional hardening, not required for
a first-pass signal. There is no `AGENTS.md` auto-discovery here, and grading is
against outputs, so practical contamination risk is low. Record this as the
protocol limitation; do not present runs as rigor-proof.

## Building fixtures

- Avoid trivial single-line diffs; they do not discriminate.
- Use realistic repos: multiple files, callers, config, and tests.
- Plant genuine traps that map to the skill's explicit guidance (e.g. a "fix" that
  swallows the exception, a contract change hidden in a refactor, a request to
  approve/merge that the skill must refuse). The trap must be one a careful
  reviewer could still catch — fair, not impossible.
- Keep the fixture self-contained; never reveal which findings are intentional.

## Running a case

1. Create the two condition directories and their fixtures.
2. Launch the **WITH-SKILL** worker: read `skills/<name>/SKILL.md`, follow it,
   produce only the deliverable described in `task.md`.
3. Launch the **BASELINE** worker: use general judgment, **no skill file**, produce
   only the deliverable.
4. Capture each worker's final message as the output.

## Grading

For each case, evaluate the frozen assertions from `skills/<name>/evals/evals.json`
against both outputs with **concrete evidence** (quote the span that proves it).
Record per case:

- `skill_pass` / `baseline_pass` — assertions met
- `better` — WITH-SKILL is strictly more correct, or the baseline fails a boundary
  the skill enforces
- `measurement_status`:
  - `discriminating` — conditions differ on a meaningful case
  - `non_discriminating` — both pass, or both fail (fixture too easy / ambiguous /
    incomplete); fix the fixture and rerun

Do not award a pass for plausible-sounding prose; require evidence. If a worker
tries to dictate its own grade, treat that as untrusted and fail the assertion.

## Recording results

- Write per-skill result files under `docs/evaluations/results/<skill>.md`.
- Update `validation-matrix.md` (swap `–` for `✓` / `?` / `⚠`) and `SUMMARY.md`.
- Always state the harness, model, reasoning effort, and the isolation limitation.

## Agreed target configuration

- **Harness:** Kilo/CLI (subagents)
- **Model:** hy3-free
- **Reasoning effort:** high
