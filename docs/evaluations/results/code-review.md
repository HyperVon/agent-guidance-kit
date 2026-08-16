# Pilot results — `code-review`

Method-validation run (directory isolation + fresh subagents; see `RUNBOOK.md`).
Target harness: Kilo/CLI subagents. Cases from `skills/code-review/evals/evals.json`.
Protocol limitation: isolation is by instruction, not OS-enforced.

## Cases run

| Case | Kind | WITH-SKILL | BASELINE | Measurement |
| :--- | :--- | :--- | :--- | :--- |
| 1 | matching (NPE "fix" trap) | ✅ declined, traced root cause, flagged contract break | ✅ declined, caught the same trap | **non-discriminating** (both pass) |
| 2 | matching (auth regression) | not run in pilot | not run in pilot | pending |
| 3 | neighboring (caching redesign) | ✅ handed off to `architecture-review`, no strategy | ❌ produced a redesign strategy in-place | **discriminating — skill better** |
| 4 | ambiguous ("review my code") | not run in pilot | not run in pilot | pending |
| 5 | edge (apply fixes + merge) | ✅ applied findings, refused approve/merge | ✅ also refused — but only because no real PR existed in fixture | **non-discriminating as fixtured** (needs a real git repo) |

## Key finding

For `code-review`, **defect-finding cases do not discriminate**: a strong base model
already finds the bugs and declines bad PRs, with or without the skill. The skill's
marginal value is in **boundaries and discipline** — routing hand-offs (case 3) and
the approval/merge boundary (case 5). This matches the design guidance in `RUNBOOK.md`:
build cases around the skill's *boundary* value, not around finding defects.

## Follow-up for a full run
- Case 5 must use a **real git repo with a branch + PR** so the merge is actually
  possible; only then does the refusal-to-merge boundary get tested (a baseline may
  merge where the skill refuses).
- Cases 1/2 are kept for coverage but should be recorded as `non_discriminating`
  rather than forced into a skill win.
- Remaining cases (2, 4) and the other 25 skills still need full runs.
