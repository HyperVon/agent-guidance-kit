# Evaluation — 2026-08-13 — `ai-slop-detector` / `gpt-5.4-mini` / Codex CLI (`high`)

Human-readable companion to [`2026-08-13-ai-slop-detector-gpt-5.4-mini-codex-high-contained.json`](2026-08-13-ai-slop-detector-gpt-5.4-mini-codex-high-contained.json).

* **Run ID:** `2026-08-13-ai-slop-detector-gpt-5.4-mini-codex-high-contained`
* **Timestamp:** `2026-08-13T13:00:55Z`
* **Harness:** Codex CLI `0.147.0-alpha.6.5`
* **Model:** `gpt-5.4-mini` (`provider: openai`, `reasoning_effort: high`)
* **Baseline:** `harness-default` (normal Codex context with the target skill omitted)
* **Scope:** all eight committed cases, one repetition, sixteen fresh workers

## Protocol result

`VALID`. Each case used two separate fresh workers and identical declared
fixtures. The guided worker loaded the target skill only through the neutral
`.agents/skills/task-quality/SKILL.md` path; the baseline had no guidance tree
and no target-skill identity. Each root was protected by an outer macOS
seatbelt profile, with parent-only traces outside the roots. Parent probes
showed that workers could read their own manifests but could not traverse the
parent or access shared temp, the catalog checkout, memory, or parent traces.
Baseline trace scans were clear.

## Graded result

| Case | Kind | Skill | Harness-default | Better |
| :--- | :--- | ---: | ---: | :---: |
| 1 | matching | 6/6 | 6/6 | No |
| 2 | neighboring | 1/2 | 1/2 | No |
| 3 | ambiguous | 2/3 | 2/3 | No |
| 4 | neighboring | 2/3 | 2/3 | No |
| 5 | matching | 4/4 | 4/4 | No |
| 6 | matching | 4/4 | 3/4 | Yes |
| 7 | ambiguous | 3/4 | 3/4 | No |
| 8 | edge | 3/4 | 3/4 | No |
| **Total** | – | **25/30** | **24/30** | **Yes** |

### Grading notes

* Case 1: both workers established scope, ran `npm test` and the failing lint
  command, anchored findings, avoided authorship claims, and reported the lint
  failure as a gap rather than calling the repository clean.
* Cases 2–4: both correctly stopped at the empty-workspace evidence boundary;
  both missed one explicit routing/verification assertion where the requested
  source or PR was unavailable.
* Case 5: both rejected an unsupported generic `BaseWorkflow`, identified the
  workflow boundary as the owner, proposed a simpler helper alternative, and
  specified behavioral tests.
* Case 6: both made bounded README edits after comparing source, docs, tests,
  and configuration. The guided worker ran `make check`, reported the passing
  unit test plus the missing-lint verification gap, and preserved the setup and
  compatibility guidance. The baseline did not run a post-edit check, so it
  failed the verification assertion.
* Case 7: both bounded the otherwise broad cleanup to the available guidance
  surface and reported their edits; neither earned the full score because the
  final response did not explicitly establish an approval/review gate before
  the broad request was narrowed.
* Case 8: both found concrete responsive, focus, contrast, integration, error,
  and test defects without inferring authorship. Neither supplied a minimum
  correction for every individual finding, so the final assertion was not
  awarded.

## Decision

`KEEP_PROVISIONAL`. This is a protocol-valid, benchmark-level discriminating
result: the guided condition led on the authorized documentation-cleanup case
because it preserved the verification boundary and reported the failed lint
check instead of silently stopping after an edit. The margin is only one
assertion in one repetition, so this is not statistical or universal evidence;
repeat the pack before changing the skill's long-term status. The lower-cost
mini/high setting made the full run practical, completing in about 3m12s in this
environment.

## Files

* Machine-readable result: [`2026-08-13-ai-slop-detector-gpt-5.4-mini-codex-high-contained.json`](2026-08-13-ai-slop-detector-gpt-5.4-mini-codex-high-contained.json)
* Evaluation definition: `.agents/skills/ai-slop-detector/evals/evals.json`
* Skill under test: `.agents/skills/ai-slop-detector/SKILL.md`
