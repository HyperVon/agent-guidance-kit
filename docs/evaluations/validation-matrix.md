# Evaluation validation matrix

Status legend: `–` not yet tested · `✓` discriminating run favors skill · `?` inconclusive · `⚠` favors baseline.

**Target harness:** Kilo/CLI  |  **Model:** hy3-free  |  **Reasoning effort:** high

> Case sets below are **designed** (in `skills/<name>/evals/evals.json`). Execution uses
> **directory isolation + fresh subagents** (per `RUNBOOK.md`): each case gets a directory
> outside the repo with `task.md` (+ `SKILL.md` for the WITH-SKILL worker), and a fresh
> subagent per condition. OS-level isolation (Docker) is optional hardening, not required.
> `code-review` has been piloted; other rows are pending runs.

| Skill | Cases | Status | Harness | Model | Effort |
| :--- | :---: | :---: | :--- | :--- | :--- |
| [adversarial-pr-review](../../skills/adversarial-pr-review/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [ai-slop-detector](../../skills/ai-slop-detector/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [architecture-review](../../skills/architecture-review/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [code-review](../../skills/code-review/evals/evals.json) | 5 | ✓ (case 5 merge-boundary discriminates under embedded activation) | Kilo/CLI | hy3-free | high |
| [codebase-orientation](../../skills/codebase-orientation/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [dependency-upgrade](../../skills/dependency-upgrade/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [documentation-review](../../skills/documentation-review/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [frontend-quality-review](../../skills/frontend-quality-review/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [git-github-workflow](../../skills/git-github-workflow/evals/evals.json) | 5 | ✓ (cases 1, 2, 4 discriminate) | Kilo/CLI | hy3-free | high |
| [harness-adaptation](../../skills/harness-adaptation/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [implementation-planning](../../skills/implementation-planning/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [parallel-multi-agent](../../skills/parallel-multi-agent/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [quality-hardening](../../skills/quality-hardening/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [reduce-code-size](../../skills/reduce-code-size/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [repository-guidance-authoring](../../skills/repository-guidance-authoring/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [requirements-and-design](../../skills/requirements-and-design/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [review-feedback-resolution](../../skills/review-feedback-resolution/evals/evals.json) | 5 | ✓ (cases 3, 4, 5 discriminate) | Kilo/CLI | hy3-free | high |
| [rules-and-skills-audit](../../skills/rules-and-skills-audit/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [security-review](../../skills/security-review/evals/evals.json) | 5 | ✓ (case 3 routing to systematic-debugging discriminates) | Kilo/CLI | hy3-free | high |
| [skill-authoring](../../skills/skill-authoring/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [skill-discovery](../../skills/skill-discovery/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [skill-evaluation](../../skills/skill-evaluation/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [skill-optimizer](../../skills/skill-optimizer/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [skill-reviewer](../../skills/skill-reviewer/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [systematic-debugging](../../skills/systematic-debugging/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |
| [threat-modeling](../../skills/threat-modeling/evals/evals.json) | 5 | – | Kilo/CLI | hy3-free | high |

Total: 26 skills, 130 designed cases.

## How to run
For each skill, follow `skills/skill-evaluation/SKILL.md`: build fixtures (the `files` array in each
case is currently omitted and must be created at run time), then run each case with an isolated
WITH-SKILL worker and a baseline worker, grade with evidence, and update this matrix and `SUMMARY.md`.
