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

- Each case gets a directory **outside the repo** with a **neutral, non-revealing
  name** — e.g. a session temp dir like `/var/folders/.../kilo/runs/run_a/`. Never put
  the skill name, `eval`, `with-skill`, or `baseline` in any path, filename, or task
  text the worker can see; that leaks the condition and biases the worker.
- The **WITH-SKILL** worker receives the target `SKILL.md` body **embedded as
  instructions directly in its prompt** (heading: "For this task, follow these
  instructions:"). This is the authoritative method — it matches how the real
  harness injects a skill into context. An optional `guide.md` file was tried and
  **under-activated** the skill (the worker ignored it and behaved like baseline),
  so do NOT use the file method for graded runs. The baseline worker gets no
  instructions.
- The **BASELINE** directory contains **only** `task.md` — no guidance file, no repo
  catalog.
- Launch a **fresh subagent** per worker (the `task` tool). Subagents do not inherit
  the parent's context, so the baseline genuinely never sees the skill.
- Instruct each worker to operate *only* inside its directory, to edit nothing, and to
  treat a missing guidance file as normal (do not go looking for one elsewhere).

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

## Standard worker prompt (paste per case)

Use this template (fill `<WORKDIR>` and the condition) for every worker. The
**containment directive is mandatory** — without it a worker can escape the case
directory and read the real repo (observed once: a BASELINE "Review my code." case
wandered into the parent project and reviewed the catalog instead of refusing). The
**names must be neutral**: never write "eval", the skill name, "with-skill", or
"baseline" in the path, the task text, or filenames.

```
Your working directory is <WORKDIR>. Read the file task.md there to understand what to do.
CRITICAL — CONTAINMENT DIRECTIVE: UNDER NO CIRCUMSTANCES may you leave <WORKDIR>.
Do not read, edit, or traverse any path outside it (no parent dirs, no /Users, no
other repos, no AGENTS.md/README/catalog). If the task references files or code
that are not present inside <WORKDIR>, treat that as "not provided" and say so.
Operate strictly within <WORKDIR> using Read/Grep/Glob/Bash( workdir=<WORKDIR> ).
[WITH-SKILL] For this task, the following instructions are in effect — follow them:
<paste the target SKILL.md body here; do NOT label it as a skill or name it>.
[BASELINE] No instructions are provided; use your own judgment.
Do not create arbitrary files; write only the required deliverable to <WORKDIR>/result.md.
```

Re-run any prior case whose output shows signs of escaping the CWD (e.g. it reviewed
files not in the fixture). Such a result is invalid and must not be graded.

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

## Cleanup (mandatory — prevents contamination and clutter)

A run directory that still holds a previous `result.md`/`output.md` will leak the
prior answer into the next worker (observed: a worker "matched" an existing
`result.md` instead of working independently). Enforce:

- **Fresh directory per run.** Never reuse a directory across runs; create a new
  neutral-named dir each time.
- **No leftover outputs.** Before launching a worker, the dir must contain only
  fixtures (`task.md`, code, design docs, git repo) — never a stale `result.md`/
  `output.md`/`__pycache__`.
- **Delete after collection.** Once both workers' outputs are graded and recorded,
  delete the case's run directories (`rm -rf <case-dir>`). At the end of a skill,
  delete the whole `runs/<skill>/` tree. The eval artifacts live in the repo
  (`docs/evaluations/`), not in the temp run dirs — there is nothing to keep.

## Agreed target configuration

- **Harness:** Kilo/CLI (subagents)
- **Model:** hy3-free
- **Reasoning effort:** high
