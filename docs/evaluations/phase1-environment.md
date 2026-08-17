# Phase 1 — environment validation (first protocol-valid evaluation attempt)

**Date:** 2026-08-16
**Goal:** prove the corrected evaluation pipeline is runnable end-to-end before scaling
to all 26 skills, using the four skills that already have frozen fixtures
(`code-review`, `git-github-workflow`, `review-feedback-resolution`, `security-review`).

**Honest conclusion up front:** this CLI environment (Kilo/CLI on a macOS laptop) can
execute the *validation and fixture* half of the pipeline, but it **cannot** execute a
protocol-valid **routing** or **execution** run. Both are recorded as `not_run`
(blocked), with the missing capability documented below. No evidence was invented and
no historical exploratory pilot was reused. See `validation-matrix.md` and `SUMMARY.md`
for the updated status.

---

## 1. Harness routing visibility

**Determination: routing evidence CANNOT be captured → routing experiments BLOCKED
(`not_run`).**

Mechanism assessed:

- The "harness" in this environment is the Kilo/CLI agent itself (the operator). There
  is no separate routing daemon, no skill-discovery service, and no startup manifest
  that emits a machine-readable *selected skill* record.
- Routing selection, when it happens, is the agent's own decision made while reading the
  prompt. There is no `loaded-skill manifest`, `routing log`, or `named tool-call` that
  surfaces the choice as harness evidence independent of the agent's prose.
- The corrected protocol (RUNBOOK §3, routing-experiments.md §A) grades routing from
  **harness-selection evidence**, not from whether the worker explains the choice.
  Prose self-report is explicitly *not* sufficient.

Because no captured `selected_skill` can be produced, the availability experiment
(target-present vs target-absent catalog) cannot be scored. Per RUNBOOK §3: "If the
harness cannot expose or verify the selected/loaded skill identity, mark the routing
comparison `protocol_status: limited` (or `not_run`) and do **not** infer routing
quality from output prose." We mark it `not_run` (blocked), the stricter of the two,
because no selection channel exists at all.

The **catalog inputs** to the experiment ARE producible here (see §4): `build_routing_catalog.py`
generates the target-present and target-absent projections correctly. Only the
*selection capture* is missing.

## 2. Isolation capability

**Determination: independent worker contexts CANNOT be created or verified → execution
efficacy runs BLOCKED (`not_run`).**

Assessed facts about this environment:

- **No OS/container isolation.** No `/.dockerenv`, no container runtime, no sandbox
  boundary. The agent runs directly on the host (`MacBook-Pro.local`).
- **No independent worker roots.** The methodology requires one WITH-SKILL worker and
  one BASELINE worker, each in its own OS-contained root, with the baseline unable to
  see the target skill's name/path/description/catalog entry through any system
  metadata. This environment has a single agent process; two independent worker roots
  cannot be spawned or verified here.
- **Host identity is present and would leak.** `git config --global --list` returns a
  personal `user.name` and `user.email`, plus a `gh` credential helper. `gh auth status`
  reports a logged-in account with a live token. Running a git fixture without the
  generator's `sanitize_env` would therefore leak the evaluator's personal identity and
  GitHub credentials — exactly the contamination that invalidated the earlier
  `git-github-workflow` case 2 pilot.
- **A single agent cannot hold two independent beliefs.** Even an instruction-only
  (`limited`) fallback requires the baseline to receive *no* target identity through any
  system metadata and a boundary probe to verify it. Because the operator already knows
  the target skill and case, baseline target-absence cannot be verified as absent from
  the worker's visible context. RUNBOOK §5: "If the harness cannot create and verify
  independent contexts … record the comparison as **invalid / not_run** and report the
  limitation. Do not score it."

Recorded values:

- **isolation method:** none available for a protocol-valid run.
- **protocol status:** `not_run` (environment cannot provide required worker isolation /
  independence). Would be at most `limited` even if a single non-isolated attempt were
  made, but independence cannot be verified, so `not_run` is the faithful classification.

> Note: the generator hashing tool (`scripts/eval_hashing.py`) *does* sanitize the
> environment when it runs fixtures (`HOME`, `XDG_CONFIG_HOME`, `GIT_CONFIG_GLOBAL`,
> `GIT_CONFIG_SYSTEM`, identity, `GH_TOKEN`, etc.), and the regenerated fixture hashes
> pass idempotently. That sanitization covers **fixture generation**, not the live
> worker run, and does not grant the runtime isolation the execution protocol requires.

## 3. Model / runtime metadata

Recorded for this environment (to be copied into any future `result-json` block once a
real harness exists):

- **harness:** Kilo/CLI
- **harness_version:** unknown
- **model:** tencent/hy3:free
- **reasoning_effort:** high
- **tools enabled:** file read/edit, bash, web fetch/search, task/subagent orchestration
- **network policy:** available (egress permitted; `https://github.com` returned HTTP 200)

These match the matrix's stated target harness
(Kilo/CLI | hy3-free | high effort). Network here is *available*, not `none`; any future
result must record the real policy rather than the schema's illustrative `none`.

---

## 4. Pipeline steps actually executed here (proven runnable)

The non-worker half of the pipeline runs green in this environment:

1. **Fixture hashing** — `python3 scripts/hash_fixtures.py` is idempotent; the six
   generator fixtures (code-review case 5, git-github-workflow cases 1–5) re-hash
   deterministically under the full git-state algorithm.
2. **Catalog generation** — `python3 scripts/build_routing_catalog.py` and
   `--target-absent <skill>` produce the routing projection for both conditions:

   ```bash
   python3 scripts/build_routing_catalog.py                            # 26 skills, target-present
   python3 scripts/build_routing_catalog.py --target-absent code-review # 25 skills, target absent
   python3 scripts/build_routing_catalog.py --target-absent git-github-workflow
   python3 scripts/build_routing_catalog.py --target-absent review-feedback-resolution
   python3 scripts/build_routing_catalog.py --target-absent security-review
   ```

   The target-absent projection correctly drops **only** the named target skill, leaving
   the other 25 entries identical (verified: present=26 rows, each absent=25 rows; the
   removed skill is exactly the one named). This is the input the availability experiment
   needs; only the selection-capture step (§1) is missing.
3. **Validation gate** — `python3 scripts/validate_evaluations.py` passes (0 hard
   errors / 0 warnings); `python3 scripts/test_validate_evaluations.py` passes (29
   tests). The gate is the part of "end-to-end" that this environment can actually
   exercise.

### Negative proof that the gate enforces the protocol

To confirm the validation pipeline rejects inflated claims (not just accepts honest
ones), a temporary result file was created claiming a `valid` run with
`instruction-only` isolation and a `both_pass` outcome, then `validate_evaluations.py`
was run against it:

```
ERR : tmp-valid-claim.md: valid run requires OS-level isolation, but isolation_method
      is 'instruction-only (limited)' (limited-grade only)
ERR : tmp-valid-claim.md case 1: contaminated/invalid result cannot claim a success
      outcome (both_pass)
```

The file was removed afterward (no fabricated result was committed). This confirms the
gate blocks the exact weakening the rules forbid: marking a limited run `valid`, and
claiming skill effectiveness from a single run.

---

## 5. Per-skill Phase 1 determinations

All four pilot skills share the same environment limits, so the routing/execution
outcome is identical; the special-attention notes below are recorded so a future
protocol-valid run knows what to watch for.

| Skill | Routing | Execution | Protocol | Repeats | Notes |
| :--- | :--- | :--- | :--- | :---: | :--- |
| code-review | not_run (blocked) | not_run (blocked) | not_run | 0 | Measure correctness, scope discipline, merge readiness, evidence-backed findings — not just obvious bugs. No run possible here. |
| git-github-workflow | not_run (blocked) | not_run (blocked) | not_run | 0 | Must use the sanitized Git environment (isolated `HOME`, no host `~/.gitconfig`, no `gh` token, deterministic repo state). Prior case 2 contamination must not recur. |
| review-feedback-resolution | not_run (blocked) | not_run (blocked) | not_run | 0 | Measure accurate feedback addressing, no unrelated changes, validation performed. |
| security-review | not_run (blocked) | not_run (blocked) | not_run | 0 | Measure systematic threat ID, evidence quality, prioritization, verification discipline — not generic model safety. |

Historical exploratory pilots for these four skills remain in
`docs/evaluations/results/` as `protocol_status: invalid` / `decision: exploratory`
evidence only and were **not** reused for this phase.

---

## 6. Recommended next phase

A protocol-valid run requires a harness that provides:

1. **Routing selection capture** — a loaded-skill manifest / routing log / named
   tool-call that records the selected skill independently of worker prose. Without it,
   routing stays `not_run`.
2. **Independent worker containment** — OS-contained WITH-SKILL and BASELINE roots (or a
   verified instruction-only fallback with a passing boundary probe and confirmed
   baseline target-absence). Without it, execution stays `not_run`.
3. **Sanitized Git/network** — the generator's `sanitize_env` pattern applied to the live
   run, plus an isolated `HOME` so the evaluator's personal `user.name` / `user.email`
   identity and `gh` token never reach the fixture or transcript.

When such a harness exists: start with these four skills (fixtures already frozen), run
the routing availability experiment (§1) and execution efficacy (§3) with ≥3
independent repetitions per condition and an optional irrelevant-guidance placebo, then
record the full `result-json` schema and retain raw evidence in `.eval-evidence/`.
