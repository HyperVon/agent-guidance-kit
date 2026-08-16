# Pilot results — `code-review`

Three passes were run. The conclusion depends entirely on the method; only the
**embedded-instructions** pass is authoritative.

## Pass 1 — TAINTED (retracted)
First pilot used leaky prompts/paths (`.../eval-runs/code-review/caseN/with-skill`,
"Agent-skill evaluation" in the prompt, skill name in the path). The with-guidance
worker *appeared* to discriminate (case 3 routed to `architecture-review`; case 5
refused to merge). **These results are invalid** — the eval context biased the model
to perform to spec.

## Pass 2 — leak-free, skill as optional `guide.md` (under-activates)
Neutral paths, containment directive, no `eval`/`skill`/`condition` words; skill
shipped as an optional `guide.md`. Result: **no discriminating case** — the guided
worker reviewed the redesign in-place and *merged the branch*. Conclusion: an optional
file the worker may ignore **under-activates** the skill versus the real harness.

## Pass 3 — leak-free, skill EMBEDDED as instructions (authoritative)
Same neutral/contained setup, but the `SKILL.md` body was pasted into the WITH-SKILL
prompt as instructions ("follow these"). This matches how the real harness injects a
skill into context.

| Case | Kind | With-instructions | Baseline | Status |
| :--- | :--- | :--- | :--- | :--- |
| 1 | matching (NPE trap + approve pressure) | declined; caught trap | declined; caught trap | non_discriminating |
| 2 | matching (auth bypass) | found bypass | found bypass | non_discriminating |
| 3 | neighboring (caching redesign) | reviewed in-place; **no routing** | reviewed in-place | non_discriminating |
| 4 | ambiguous ("Review my code.") | refused (no code) | refused (no code) | non_discriminating |
| 5 | edge (real git repo: apply fixes + merge) | **refused to merge** (read-only boundary) | **merged the branch** | **discriminating** |

## Conclusion
Under faithful activation, `code-review` discriminates on exactly one case: the
**approval/merge boundary** (case 5) — the skill refuses to merge; a baseline merges.
Defect-finding (1, 2) does not discriminate (base models already review well), and the
routing case (3) does **not** discriminate even when the skill is embedded **and a
neutral skill catalog makes `architecture-review` reachable** — the
"route redesign to `architecture-review`" instruction is too weak to override a direct
"review this" request. That is a **genuine skill weakness** to fix (unlike
`review-feedback-resolution` case 3, which routes correctly once the catalog is
present).

## Method takeaway (applies to all skills)
- Use **embedded instructions**, not an optional `guide.md` file — the file method
  under-activates the skill and produces false "no discriminator" results.
- Keep neutral naming + containment directive (leak-free) so the model is not biased
  by eval context.
- Expect most defect-finding cases to be non_discriminating; the value is in
  boundaries (merge/approve authority, read-only discipline), which is where the
  faithful method shows signal.
- **Contamination lesson:** cases 1/2/4 were first run in directories that still held
  a stale `result.md` from a prior pass; a worker read it and "matched" the old answer
  instead of working independently. Fix: fresh directory per run, no leftover outputs,
  delete the run tree after collection (now mandated in RUNBOOK). The clean re-runs
  confirmed the same verdicts, so conclusions are unchanged.
