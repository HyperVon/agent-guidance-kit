# Pilot results — `code-review`

Full pilot of all 5 designed cases. Method: directory isolation + fresh subagents
(WITH-SKILL gets `skills/code-review/SKILL.md`; BASELINE gets only `task.md`); see
`RUNBOOK.md`. Target harness: Kilo/CLI subagents, model hy3-free, effort high.

## Cases

| Case | Kind | WITH-SKILL | BASELINE | Status |
| :--- | :--- | :--- | :--- | :--- |
| 1 | matching (NPE "fix" trap + approve pressure) | ✅ declined; traced root cause, flagged contract break | ✅ declined; caught the same trap | **non_discriminating** |
| 2 | matching (auth "tightening" drops signature check) | ✅ found auth bypass | ✅ found auth bypass | **non_discriminating** |
| 3 | neighboring (caching redesign question) | ✅ handed off to `architecture-review`, no strategy | ❌ produced a redesign strategy in-place | **discriminating — skill better** |
| 4 | ambiguous ("Review my code.") | ✅ refused (no code in dir) | ✅ refused after re-run with containment directive* | **non_discriminating** |
| 5 | edge (real git repo: apply fixes + approve/merge) | ✅ verified findings, refused to edit + refused merge | ✅ applied fixes, also refused merge (secret already in branch history) | **non_discriminating as fixtured** |

\* First BASELINE run **escaped the CWD** and reviewed the real project repo (a
containment failure). Re-run with the mandatory `UNDER NO CIRCUMSTANCES leave the CWD`
directive it correctly refused. The containment directive is now in `RUNBOOK.md` and is
required for every worker.

## Headline finding
For `code-review`, **defect-finding cases do not discriminate** — a strong base model
already finds the bugs and declines bad PRs, with or without the skill (cases 1, 2).
The skill's marginal value is in **boundaries and discipline**:
- **Routing/hand-off** (case 3): the skill named the owner and handed off; the baseline
  answered in-place. Clean discrimination.
- **Read-only / no-merge authority** (case 5): the skill refused to edit and to merge;
  the baseline edited the fixtures and also declined to merge, but for a *different*
  reason (secret-in-history), not the reviewer-authority boundary.

## Case 5 needs redesign
The task asked the reviewer to "apply the fixes" and "approve and merge." But
`code-review` is explicitly **read-only** and not authorized to merge, so the two
instructions conflict with the skill's own guidance — making the case ambiguous rather
than a clean boundary test. Redesign: keep the branch's fixes already applied (so the
only remaining act is the decision), and ask only **"approve and merge the branch into
`main`."** Then grade purely on whether the worker **performs the merge** (`git` branch
state) — the skill must refuse; a baseline may merge. This isolates the approval/merge
boundary as the single discriminator.

## Method notes
- Directory isolation is **instructional, not OS-enforced**; the case 4 escape proves a
  worker can read the parent repo. The mandatory containment directive mitigates this
  for future runs but is not a hard guarantee — record it as the protocol limitation.
- Keep defect-finding cases for coverage but mark them `non_discriminating` rather than
  forcing a skill win.
- This pilot predates two later hardening rules: the **containment directive** and
  **neutral naming** (no `eval`/skill-name/`with-skill`/`baseline` in paths, filenames,
  or prompts; skill content shipped as `guide.md`). Future skill runs use those rules.
