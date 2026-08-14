# Evaluation run — 2026-08-14 — threat-modeling / gemini-flash-lite / Antigravity

Human-readable companion to [`2026-08-14-threat-modeling-gemini-flash-lite-antigravity.json`](2026-08-14-threat-modeling-gemini-flash-lite-antigravity.json) (machine-readable, validated by `scripts/validate_repository.py`).

* **Run ID:** `2026-08-14-threat-modeling-gemini-flash-lite-antigravity`
* **Timestamp:** `2026-08-14T01:23:00Z`
* **Harness:** `Antigravity` `2.0.0`
* **Model:** `gemini-flash-lite` (`provider: google`, `reasoning_effort: low`)
* **Baseline:** `harness-default` (clean context; general software engineering assistant without `threat-modeling` skill)
* **Skill commit:** `22f91d9`
* **Method:** Executed live with 6 independent subagents via `invoke_subagent` on Gemini Flash Lite (`low` effort). 3 `WITH-SKILL` sessions (`eval_guided_worker_threat_modeling`) and 3 `BASELINE` sessions (`eval_baseline_worker`) were launched concurrently across the 3 frozen cases in `evals/evals.json`. Assertions were graded directly against the returned subagent transcripts with concrete quoted evidence.

## Summary

| Skill | Cases | Skill pass / Total | Baseline pass / Total | Better | Decision |
| :--- | ---: | ---: | ---: | :---: | :--- |
| `threat-modeling` | 3 | 5/9 | 4/9 | ✓ | `KEEP_PROVISIONAL` |

## Per-case detail

### `threat-modeling`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill vs baseline) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 4 | 4/4 | 3/4 | ✓ | (1) skill & baseline mapped concrete components, entrypoints, assets, trust boundaries (2) skill & baseline calibrated attacker capabilities vs non-capabilities and tied abuse paths (3) **skill win**: skill explicitly separated existing mitigations, recommendations, and assumptions/unknowns (Section 7), whereas baseline omitted explicit assumptions and unknowns (4) both remained strictly report-only without live probing |
| 2 | neighboring | 2 | 1/2 | 1/2 | – | Both workers directly reviewed the authentication vulnerability in the patch without expanding into a system-wide threat model (assertion 2 pass for both), but neither worker explicitly cited `security-review` by name in their output (assertion 1 missed by both) |
| 3 | ambiguous | 3 | 0/3 | 0/3 | – | Both workers evaluated repository security documentation and concluded the architecture "appears secure", missing the requirement to clarify missing deployment/exposure context, state the threat-modeling vs security-review routing distinction, and refuse a secure verdict |

**Evaluator review notes:**
In the matching case, the guided worker demonstrated structured threat modeling discipline by explicitly documenting underlying assumptions and unresolved unknowns alongside existing and recommended mitigations, which the baseline omitted. In the neighboring case, both workers properly scoped their analysis to the auth vulnerability without building an unwanted threat model. In the ambiguous case, both `gemini-flash-lite` workers fell into the trap of issuing an ungrounded "secure" verdict rather than probing for missing deployment/operational context; this highlights an area for future benchmark hardening or extended reasoning effort. Human reviewer can add manual observations here.
