# Agent Guidance Kit

Agent Guidance Kit is a portable collection of software-engineering agent
skills that you can review, copy, and adapt into a compatible coding-agent
environment. It is a library, not an installer, runtime, package manager, or
certification system.

## Browse

Start with the catalog below. Each skill is a self-contained `SKILL.md` with
optional reference material loaded when needed.

## Review

Read the `SKILL.md` and any relevant references for the skills that match your
workflow. Check their trigger, boundaries, assumptions, and portability before
adopting them.

## Select

Choose only the skills that fit your project. A useful adoption decision is
`ADD`, `ADAPT`, `KEEP_LOCAL`, `DEFER`, or `SKIP`.

## Copy and Adapt

1. Copy the selected skill folder into your agent's supported skill location.
2. Adapt project-specific names, commands, and boundaries.
3. Keep local guidance that is stronger or more specific than the copied skill.
4. Review the result in the context of your project before using it.

The detailed adoption workflow is in
[`docs/using-the-library.md`](docs/using-the-library.md).

## Included Skills

| Skill | What it does |
| :--- | :--- |
| [adversarial-pr-review](skills/adversarial-pr-review/SKILL.md) | Parent-validated adversarial PR review using a fresh independent subagent; partitions large diffs into bounded tracks and re-reviews until convergence. |
| [ai-slop-detector](skills/ai-slop-detector/SKILL.md) | Audit artifacts for plausible-but-harmful quality defects: AI slop, invented APIs, misleading tests/docs, needless complexity. |
| [architecture-review](skills/architecture-review/SKILL.md) | Fresh-eyes architecture review comparing Keep / Evolve / Replace / Greenfield options; recommends only. |
| [code-review](skills/code-review/SKILL.md) | Evidence-based review of diffs, branches, and subsystems for correctness, contract, security, and test defects; report-first. |
| [codebase-orientation](skills/codebase-orientation/SKILL.md) | Map and explain unfamiliar repositories from evidence: purpose, stack, structure, entry points, workflows, modules, integrations, config, tests, conventions, unknowns. |
| [dependency-upgrade](skills/dependency-upgrade/SKILL.md) | Safely upgrade pinned dependencies: inventory, security-first, group by risk, verify after each group. |
| [documentation-review](skills/documentation-review/SKILL.md) | Sync docs to implementation, build, config, tests, and CI truth; factual accuracy only. |
| [frontend-quality-review](skills/frontend-quality-review/SKILL.md) | Evidence-based UI/UX quality, interaction, accessibility, responsive, and performance review. |
| [git-github-workflow](skills/git-github-workflow/SKILL.md) | Git hygiene and GitHub collaboration: branches, commits, PRs, issues, releases; approval-gated. |
| [harness-adaptation](skills/harness-adaptation/SKILL.md) | Adapt a repository's canonical guidance to the active harness without creating a second source of truth. |
| [implementation-planning](skills/implementation-planning/SKILL.md) | Create execution-ready implementation plans from approved designs: objective, files, ordering, contracts, migration, tasks, verification, risks. |
| [parallel-multi-agent](skills/parallel-multi-agent/SKILL.md) | Partition work into bounded concurrent workers with disjoint ownership and parent-owned integration. |
| [quality-hardening](skills/quality-hardening/SKILL.md) | Bounded evidence-first QA loop: baseline, find gaps, add regression tests, minimal fixes, re-verify. |
| [reduce-code-size](skills/reduce-code-size/SKILL.md) | Shrink or split code while preserving behavior, contracts, and verification; measure first. |
| [repository-guidance-authoring](skills/repository-guidance-authoring/SKILL.md) | Create canonical agent instructions (AGENTS.md, onboarding) from repository reality; separate discovered facts from team policy. |
| [requirements-and-design](skills/requirements-and-design/SKILL.md) | Clarify desired behavior and design choices before implementation: outcome, requirements, constraints, acceptance criteria, approach. |
| [review-feedback-resolution](skills/review-feedback-resolution/SKILL.md) | Resolve incoming review comments against repository evidence: disposition each item, apply accepted fixes, reject unsupported ones. |
| [rules-and-skills-audit](skills/rules-and-skills-audit/SKILL.md) | Audit agent rules and skills for overlap, conflicts, unclear triggers, and consolidation opportunities. |
| [security-review](skills/security-review/SKILL.md) | Evidence-based review of changes, boundaries, and workflows for secrets, auth, input, data exposure, and dependency risks. |
| [skill-authoring](skills/skill-authoring/SKILL.md) | Author or revise a repository-local agent skill after approval, preserving trigger, boundaries, and portability. |
| [skill-discovery](skills/skill-discovery/SKILL.md) | Proactively search GitHub, harness docs, and public guidance for candidate agent workflows and map them to a project's existing skill catalog (evidence table for skill-reviewer intake). |
| [skill-optimizer](skills/skill-optimizer/SKILL.md) | Lower guidance context cost without weakening routing, safety, correctness, or verification. |
| [skill-reviewer](skills/skill-reviewer/SKILL.md) | Review skills and guidance for missing, weak, or misleading content and recommend improvements. |
| [systematic-debugging](skills/systematic-debugging/SKILL.md) | Diagnose a reproducible failure by finding its root cause before fixing. |
| [threat-modeling](skills/threat-modeling/SKILL.md) | Repository-grounded threat model: assets, actors, boundaries, entrypoints, abuse paths, mitigations. |

## Evaluation Ownership

Evaluation corpus, evidence, and methodology are maintained separately in
[`agent-guidance-kit-evals`](https://github.com/HyperVon/agent-guidance-kit-evals).
You do not need that repository to browse, select, copy, or use a skill from
this library.

## License

Apache License 2.0. See [LICENSE](LICENSE).
