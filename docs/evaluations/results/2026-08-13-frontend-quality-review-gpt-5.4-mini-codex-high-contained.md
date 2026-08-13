# Evaluation — 2026-08-13 — `frontend-quality-review` / `gpt-5.4-mini` / Codex CLI (`high`)

Human-readable companion to [`2026-08-13-frontend-quality-review-gpt-5.4-mini-codex-high-contained.json`](2026-08-13-frontend-quality-review-gpt-5.4-mini-codex-high-contained.json).

* **Run ID:** `2026-08-13-frontend-quality-review-gpt-5.4-mini-codex-high-contained`
* **Timestamp:** `2026-08-13T12:38:42Z`
* **Harness:** Codex CLI `0.147.0-alpha.6.5`
* **Model:** `gpt-5.4-mini` (`provider: openai`, `reasoning_effort: high`)
* **Baseline:** `harness-default` (normal Codex context with the target skill omitted)
* **Scope:** all five committed frontend cases, one repetition, ten fresh workers

## Protocol result

`VALID`. Each case used two separate fresh workers and identical declared
fixtures. The guided worker loaded the target skill only through the neutral
`.agents/skills/task-quality/SKILL.md` path; the baseline had no guidance tree
and no target-skill identity. Each root was protected by an outer macOS
seatbelt profile, with parent-only traces outside the roots. Parent probes
showed that workers could read their own manifests but could not traverse the
parent or access shared temp, the catalog checkout, memory, or parent traces.
Baseline trace scans were clear. The interrupted Luna/max case-2 attempt was
excluded from this run.

## Graded result

| Case | Kind | Skill | Harness-default | Better |
| :--- | :--- | ---: | ---: | :---: |
| 1 | matching | 3/5 | 3/5 | No |
| 2 | matching | 3/3 | 3/3 | No |
| 3 | neighboring | 3/3 | 3/3 | No |
| 4 | ambiguous | 3/3 | 3/3 | No |
| 5 | edge | 4/4 | 4/4 | No |
| **Total** | – | **16/18** | **16/18** | **No** |

### Grading notes

* Case 1: both workers found concrete responsive/accessibility or purchase-flow
  defects and stayed report-only. Neither final response explicitly stated the
  source-only verification limit or supplied a verification probe for each
  finding, so those two assertions were not passed.
* Case 2: both connected accessibility concerns to concrete actions/states,
  identified the static smoke test's browser-coverage gap, and reported only
  high-impact issues without edits.
* Case 3: both routed the backend task correctly, inspected the implementation
  and tests, made a small backend fix, and ran the declared check. The check
  target was initially miswired to npm; both workers surfaced and corrected it
  before claiming success.
* Case 4: both bounded the request, asked for the missing workspace/breakpoint
  evidence, and declined to claim responsive verification from an empty fixture.
* Case 5: both identified source-confirmed release risks, covered validation or
  success/failure concerns, listed browser/payment-system gaps, and remained
  report-only.

## Decision

`INCONCLUSIVE`. This is a protocol-valid full-pack run and demonstrates that a
lower-cost fixed model/effort can make broad screening practical (about 2m43s
wall-clock with independent pairs run concurrently in this environment). It is
not evidence that the skill is ineffective: the baseline reached the same
assertion outcome, and this is only one repetition. The Luna/max pilot remains
separate historical evidence; model/effort results must not be combined.

## Files

* Machine-readable result: [`2026-08-13-frontend-quality-review-gpt-5.4-mini-codex-high-contained.json`](2026-08-13-frontend-quality-review-gpt-5.4-mini-codex-high-contained.json)
* Evaluation definition: `.agents/skills/frontend-quality-review/evals/evals.json`
* Skill under test: `.agents/skills/frontend-quality-review/SKILL.md`
