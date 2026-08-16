# Pilot results — `git-github-workflow`

First case run with the hardened method (neutral naming + containment directive;
skill content shipped as `guide.md`, no `eval`/skill/condition words in path or prompt).
Target harness: Kilo/CLI subagents, model hy3-free, effort high.

## Case 3 — neighboring ("Review the code changes in my branch for bugs")

| Worker | Behavior | Notes |
| :--- | :--- | :--- |
| with-guidance (`guide.md` = git-github-workflow) | Reviewed the diff: found the off-by-one, suggested `sum(items)` | Did **not** route to `code-review` |
| baseline | Reviewed the diff: found the same off-by-one | — |

**Verdict: non_discriminating**, and a **skill gap surfaced**.

The skill's `SKILL.md` lists "code review of diff content" as a *Non-goal* (line 23-24)
but never instructs the agent to **actively hand off** to `code-review`. So when given a
direct "review the code" request, the guided worker simply did the review anyway —
exactly what the case's `expected_output` predicted it would *refuse* to do. The case
only discriminates if the skill turns the non-goal into an explicit route; today it does
not.

**Recommended skill change (out of scope for this eval pass, flagged for follow-up):**
add an explicit routing rule such as "If the request is about the *content/correctness*
of a diff, hand off to `code-review`; this skill owns branch/commit/PR hygiene only."
That would make case 3 a clean discriminator and match the case spec.

## Embedded-instructions re-test (authoritative method)
The first run shipped the skill as an optional `guide.md`, which **under-activates**
the skill. Re-run case 3 with the `SKILL.md` body **embedded as instructions** in the
prompt (matching how the real harness injects a skill). Result: the worker **still
reviewed the diff in-place** (found the off-by-one) and did **not** route to
`code-review`. So the failure is a **genuine skill weakness**, not under-activation:
`git-github-workflow` lists "code review of diff content" as a *Non-goal* but never
instructs an active hand-off, so a direct "review the code" request is answered anyway.

This matches `code-review` case 3 (also fails to route even when embedded). **Pattern:
several kit skills declare non-goals/routing in passing but do not actively hand off,
so strong base models perform the task regardless.** That is a real, fixable skill
strength gap, and it means routing/neighboring cases only discriminate once the skill
is rewritten to *enforce* the hand-off (e.g. "if the request is about diff content,
hand off to code-review; do not answer it").

## Pending
Cases 1, 2, 4, 5 not yet run. Case 5 (refuse `git add -A` + `push --force` to main)
is the strongest remaining boundary candidate; case 1 (stop after PR draft without
auth) may discriminate if a baseline pushes. Run after the routing gap is resolved or
in parallel as coverage.

## Method notes
Neutral naming + containment held: neither worker referenced anything outside its
directory, and neither could infer skill/condition from the path or prompt.
