# Evaluation run — 2026-08-13 — `frontend-quality-review` / `gpt-5.6-luna` / Codex CLI (`max`)

Human-readable companion to [`2026-08-13-frontend-quality-review-gpt-5.6-luna-codex-max.json`](2026-08-13-frontend-quality-review-gpt-5.6-luna-codex-max.json).

* **Run ID:** `2026-08-13-frontend-quality-review-gpt-5.6-luna-codex-max`
* **Timestamp:** `2026-08-13T09:32:11Z`
* **Harness:** Codex CLI `0.147.0-alpha.6.5`
* **Model:** `gpt-5.6-luna` (`provider: openai`, `reasoning_effort: max`)
* **Baseline:** `harness-default` (normal Codex context with the target skill omitted)
* **Skill snapshot:** uncommitted working-tree `SKILL.md`, SHA-256 `d647466a09c238fcfd8272096599eb27e057f01ade96e46298ff31e154f4dc33`
* **Evaluation snapshot:** `evals/evals.json` SHA-256 `43ce683f4da6e64ed5d8b8f38539327712fc5b0aabc1ca3e30a0e252b33eea93`

## Protocol verification

This was a valid isolated-runner canary, not a role-played baseline.

| Check | Evidence |
| :--- | :--- |
| Fresh workers | Six distinct Codex CLI sessions: one guided and one baseline session for each of the three cases. |
| Actual workspace | Each worker started in its own neutral fixture root; the parent verified `pwd` and the immediate visible-file manifest. |
| Guidance boundary | Guided roots contained the skill only at neutral path `.agents/skills/task-quality/SKILL.md`; baseline roots contained no `.agents` tree. |
| `AGENTS.md` boundary | Guided and baseline roots used different neutral variants. The baseline variant did not mention guidance, missing guidance, a condition, or an `if-exists` rule. |
| Fixture parity | Declared fixture files were byte-identical between conditions; their hashes are recorded in the machine result. |
| Trace boundary | Raw stdout, stderr, and session JSONL were captured outside both worker roots, so workers could not inspect their own traces. |
| Worker blindness | Workers received only the natural task prompt and available files, not assertions, expected outputs, rubric, condition labels, or evaluation instructions. |
| Parent grading | The parent inspected the completed sessions and graded the frozen assertions from their outputs. |

The target skill identity, evaluation metadata, and catalog paths were absent from the baseline-visible roots and baseline traces. No invalid or contaminated run is included in this result.

## Results

| Case | Kind | Assertions | Skill | Baseline | Better |
| ---: | :--- | ---: | ---: | ---: | :---: |
| 1 | matching | 4 | 4/4 | 4/4 | No |
| 2 | neighboring | 2 | 1/2 | 1/2 | No |
| 3 | ambiguous | 3 | 1/3 | 1/3 | No |
| **Total** | — | **9** | **6/9** | **6/9** | **No** |

### Case 1 — matching

Both workers produced useful source-only UI reviews with precise file evidence. Both established the absence of rendered screenshots, browser traces, and real payment integration, covered responsive behavior, accessibility, states, and verification limits, and stayed report-only. The baseline was already strong enough to pass all four frozen assertions, so the skill showed no measurable advantage on this fixture.

### Case 2 — neighboring

Both workers correctly avoided inventing a frontend audit when the workspace contained no backend checkout or diff. The guided worker noted during progress that the frontend-specific guidance was not applicable, but its final response did not explicitly name `code-review` or `security-review`; the strict first assertion was therefore not awarded. Both passed the second assertion.

### Case 3 — ambiguous

Both workers made no edits because the evaluation workspace was read-only, so both passed the no-edit assertion. Neither requested or established the missing product intent and scope, nor clearly distinguished review from implementation or subjective redesign before acting. The guided worker planned a redesign; the baseline identified concrete page changes. Those behaviors did not satisfy the first two frozen assertions.

## Decision

`INCONCLUSIVE`.

The isolation and grading protocol passed inspection, but this smoke run did not discriminate the target skill from the harness-default worker: both conditions scored 6/9. The result is valid protocol evidence with an inconclusive measurement, not evidence that the skill is ineffective. The benchmark should be strengthened before making a skill decision; no full-catalog run was started.

The result also identifies useful follow-up questions for a later revision: whether the neighboring-case routing language should require an explicit owner in the final answer, and whether the ambiguous case should be handled by a broader implementation/planning owner rather than this report-only skill.

## Files

* Machine-readable result: [`2026-08-13-frontend-quality-review-gpt-5.6-luna-codex-max.json`](2026-08-13-frontend-quality-review-gpt-5.6-luna-codex-max.json)
* Evaluation definition: `.agents/skills/frontend-quality-review/evals/evals.json`
* Skill under test: `.agents/skills/frontend-quality-review/SKILL.md`
* Matrix: [`validation-matrix.md`](../validation-matrix.md)
