# Agent Guidance Kit

A portable library of agent skills you **copy or adapt** into your own project.
There is no installer and no adoption lifecycle — you read the skills here and
adopt the ones that fit. Check out the repo, then ask your coding agent to
review it and recommend what to adopt.

See [`docs/using-the-library.md`](docs/using-the-library.md) for the exact
review-and-adopt workflow your agent should follow.

## Included skills

| Skill | What it does |
| :--- | :--- |
| [adversarial-pr-review](skills/adversarial-pr-review/SKILL.md) | Parent-validated adversarial PR review using a fresh independent subagent; partitions large diffs into bounded tracks and re-reviews until convergence. |
| [ai-slop-detector](skills/ai-slop-detector/SKILL.md) | Audit artifacts for plausible-but-harmful quality defects: AI slop, invented APIs, misleading tests/docs, needless complexity. |
| [architecture-review](skills/architecture-review/SKILL.md) | Fresh-eyes architecture review comparing Keep / Evolve / Replace / Greenfield options; recommends only. |
| [codebase-orientation](skills/codebase-orientation/SKILL.md) | Map and explain unfamiliar repositories from evidence: purpose, stack, structure, entry points, workflows, modules, integrations, config, tests, conventions, unknowns. |
| [code-review](skills/code-review/SKILL.md) | Evidence-based review of diffs, branches, and subsystems for correctness, contract, security, and test defects; report-first. |
| [dependency-upgrade](skills/dependency-upgrade/SKILL.md) | Safely upgrade pinned dependencies: inventory, security-first, group by risk, verify after each group. |
| [documentation-review](skills/documentation-review/SKILL.md) | Sync docs to implementation, build, config, tests, and CI truth; factual accuracy only. |
| [frontend-quality-review](skills/frontend-quality-review/SKILL.md) | Evidence-based UI/UX quality, interaction, accessibility, responsive, and performance review. |
| [git-github-workflow](skills/git-github-workflow/SKILL.md) | Git hygiene and GitHub collaboration: branches, commits, PRs, issues, releases; approval-gated. |
| [harness-adaptation](skills/harness-adaptation/SKILL.md) | Adapt a repository's canonical guidance to the active harness without creating a second source of truth. |
| [implementation-planning](skills/implementation-planning/SKILL.md) | Create execution-ready implementation plans from approved designs: objective, files, ordering, contracts, migration, tasks, verification, risks. |
| [parallel-multi-agent](skills/parallel-multi-agent/SKILL.md) | Partition work into bounded concurrent workers with disjoint ownership and parent-owned integration. |
| [quality-hardening](skills/quality-hardening/SKILL.md) | Bounded evidence-first QA loop: baseline, find gaps, add regression tests, minimal fixes, re-verify. |
| [reduce-code-size](skills/reduce-code-size/SKILL.md) | Shrink or split code while preserving behavior, contracts, and verification; measure first. |
| [requirements-and-design](skills/requirements-and-design/SKILL.md) | Clarify desired behavior and design choices before implementation: outcome, requirements, constraints, acceptance criteria, approach. |
| [repository-guidance-authoring](skills/repository-guidance-authoring/SKILL.md) | Create canonical agent instructions (AGENTS.md, onboarding) from repository reality; separate discovered facts from team policy. |
| [rules-and-skills-audit](skills/rules-and-skills-audit/SKILL.md) | Audit agent rules and skills for overlap, conflicts, unclear triggers, and consolidation opportunities. |
| [review-feedback-resolution](skills/review-feedback-resolution/SKILL.md) | Resolve incoming review comments against repository evidence: disposition each item, apply accepted fixes, reject unsupported ones. |
| [security-review](skills/security-review/SKILL.md) | Evidence-based review of changes, boundaries, and workflows for secrets, auth, input, data exposure, and dependency risks. |
| [skill-authoring](skills/skill-authoring/SKILL.md) | Author or revise a repository-local agent skill after approval, preserving trigger, boundaries, and portability. |
| [skill-evaluation](skills/skill-evaluation/SKILL.md) | Design or run clean-context evaluations to decide whether a skill improves outcomes. |
| [skill-optimizer](skills/skill-optimizer/SKILL.md) | Lower guidance context cost without weakening routing, safety, correctness, or verification. |
| [skill-reviewer](skills/skill-reviewer/SKILL.md) | Review skills and guidance for missing, weak, or misleading content and recommend improvements. |
| [systematic-debugging](skills/systematic-debugging/SKILL.md) | Diagnose a reproducible failure by finding its root cause before fixing. |
| [threat-modeling](skills/threat-modeling/SKILL.md) | Repository-grounded threat model: assets, actors, boundaries, entrypoints, abuse paths, mitigations. |

## Adopting guidance

1. Check out this repo.
2. In your project, ask your agent to read this `README.md` and the catalog, then
   decide for each skill whether to `ADD`, `ADAPT`, `KEEP_LOCAL`, `DEFER`, or
   `SKIP` it.
3. Approve the plan, then let the agent copy or adapt the chosen skills.

Full workflow: [`docs/using-the-library.md`](docs/using-the-library.md).

## License

Apache License 2.0. See [LICENSE](LICENSE).
