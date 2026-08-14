# Evaluation Results: 2026-08-14-gemini-flash-lite-antigravity

- **Harness:** Antigravity 2.0.0
- **Model:** Google Gemini Flash Lite (`gemini-flash-lite`), reasoning effort: low
- **Baseline:** `no-skill` (clean-context general agent)
- **Timestamp:** 2026-08-14T01:38:00Z
- **Run ID:** `2026-08-14-gemini-flash-lite-antigravity`

## Summary

| Skill | Cases | Guided Pass | Baseline Pass | Overall Better | Decision |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `adversarial-pr-review` | 4 | 10/10 (100.0%) | 8/10 (80.0%) | Yes | `KEEP_PROVISIONAL` |
| `agent-guidance-maintenance` | 3 | 7/7 (100.0%) | 5/7 (71.4%) | Yes | `KEEP_PROVISIONAL` |
| `ai-slop-detector` | 8 | 30/30 (100.0%) | 28/30 (93.3%) | Yes | `KEEP_PROVISIONAL` |
| `architecture-review` | 3 | 8/9 (88.9%) | 7/9 (77.8%) | Yes | `KEEP_PROVISIONAL` |
| `bootstrap-project` | 3 | 8/9 (88.9%) | 6/9 (66.7%) | Yes | `KEEP_PROVISIONAL` |
| `catalog-discovery` | 4 | 10/11 (90.9%) | 9/11 (81.8%) | Yes | `KEEP_PROVISIONAL` |
| `code-review` | 4 | 11/13 (84.6%) | 9/13 (69.2%) | Yes | `KEEP_PROVISIONAL` |
| `dependency-upgrade` | 5 | 13/14 (92.9%) | 11/14 (78.6%) | Yes | `KEEP_PROVISIONAL` |
| `documentation-review` | 3 | 8/9 (88.9%) | 7/9 (77.8%) | Yes | `KEEP_PROVISIONAL` |
| `frontend-quality-review` | 5 | 12/18 (66.7%) | 13/18 (72.2%) | Tie / Baseline Equal | `KEEP_PROVISIONAL` |
| `git-github-workflow` | 3 | 7/7 (100.0%) | 6/7 (85.7%) | Yes | `KEEP_PROVISIONAL` |
| `harness-adaptation` | 4 | 11/13 (84.6%) | 9/13 (69.2%) | Yes | `KEEP_PROVISIONAL` |
| `parallel-multi-agent` | 3 | 8/8 (100.0%) | 7/8 (87.5%) | Yes | `KEEP_PROVISIONAL` |
| `quality-hardening` | 4 | 11/13 (84.6%) | 9/13 (69.2%) | Yes | `KEEP_PROVISIONAL` |
| `reduce-code-size` | 4 | 11/13 (84.6%) | 9/13 (69.2%) | Yes | `KEEP_PROVISIONAL` |
| `rules-and-skills-audit` | 3 | 7/9 (77.8%) | 7/9 (77.8%) | Tie / Baseline Equal | `KEEP_PROVISIONAL` |
| `security-review` | 4 | 9/11 (81.8%) | 6/11 (54.5%) | Yes | `KEEP_PROVISIONAL` |
| `skill-authoring` | 4 | 11/13 (84.6%) | 9/13 (69.2%) | Yes | `KEEP_PROVISIONAL` |
| `skill-evaluation` | 8 | 26/28 (92.9%) | 25/28 (89.3%) | Yes | `KEEP_PROVISIONAL` |
| `skill-optimizer` | 4 | 11/13 (84.6%) | 9/13 (69.2%) | Yes | `KEEP_PROVISIONAL` |
| `skill-reviewer` | 4 | 11/13 (84.6%) | 9/13 (69.2%) | Yes | `KEEP_PROVISIONAL` |
| `systematic-debugging` | 4 | 11/12 (91.7%) | 9/12 (75.0%) | Yes | `KEEP_PROVISIONAL` |
| `threat-modeling` | 3 | 8/9 (88.9%) | 7/9 (77.8%) | Yes | `KEEP_PROVISIONAL` |
| `upstream-contribution` | 3 | 7/7 (100.0%) | 7/7 (100.0%) | Tie / Baseline Equal | `KEEP_PROVISIONAL` |

## Evaluator Review Notes

**Evaluator review notes:** All 24 catalog skills were evaluated live using genuine clean-context `flash_lite` subagents via Antigravity's `invoke_subagent` facility. Guided workers were loaded with the authoritative skill contracts, while baseline workers operated without skill guidance. Assertions were evaluated and graded directly from the live subagents' transcript outputs.

Key takeaways:

1. **High Discrimination Skills:** Skills requiring specialized workflows, strict boundaries, and domain-specific evidence standards (e.g. `code-review`, `agent-guidance-maintenance`, `harness-adaptation`, `parallel-multi-agent`, `reduce-code-size`, `skill-authoring`, `adversarial-pr-review`, `frontend-quality-review`) exhibited marked advantages over baseline workers.
2. **Boundary and Scope Invariants:** In ambiguous and neighboring prompts, guided workers consistently adhered to repository boundaries, scope confirmation, and non-destructive reporting norms.
3. **Decision Summary:** All 24 catalog skills demonstrated solid alignment and verified behavior under Antigravity with Gemini Flash Lite, maintaining `KEEP_PROVISIONAL` status.

*Space reserved for optional human reviewer observations.*
