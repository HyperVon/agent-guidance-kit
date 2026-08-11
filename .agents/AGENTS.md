# Agent Guidance Kit rules

This repository is a portable library of project-local agent skills and a
bootstrap workflow for adopting only the guidance an existing software project
actually needs.

## Product boundary

The active coding harness and its current LLM perform semantic work: inspect the
target repository, understand its constraints, select useful skills, reconcile
them with local guidance, identify the harness's relevant capabilities, and
explain the proposed integration.

Deterministic helpers may inventory files, calculate hashes, validate structure,
and copy an approved set of files safely. They must not classify the project,
select skills, call an LLM, fetch remote content, install a provider, route a
model, or supervise workers.

Keep provider/model routing, quota policy, process supervision, worktree worker
ownership, and recovery in a separate future runtime project. Do not add those
systems here.

## Repository invariants

- Keep the root `AGENTS.md` and harness entrypoints thin. Canonical project
  policy lives here; portable always-on behavior lives in `OPERATING.md`; deep
  procedures live in skills.
- Adapt to harness capabilities rather than maintaining a closed product
  allowlist. Known harness profiles are evidence and examples, not runtime
  gates; unknown harnesses use the capability contract and manual fallback.
- Prefer a small focused skill with a precise trigger over a broad framework or
  a second representation of the same guidance.
- Treat target-project guidance as authoritative. Adoption is proposal-first
  and approval-gated. New content is create-only; receipt-owned content may be
  refreshed only while its target digest is unchanged; local divergence fails
  closed.
- Do not execute copied or external scripts while reviewing guidance. Do not
  fetch, install, authenticate, start services, or contact external systems as
  part of bootstrap.
- Keep target-facing adoption and inventory helpers deterministic,
  standard-library Python, network-free, and safe against path traversal,
  symlink escapes, undeclared dependency links, partial conflict application,
  and implicit overwrites.
  Repository-only validators may use small declared development dependencies
  when they materially improve format validation.
- Keep examples generic. Never commit personal paths, usernames, hostnames,
  credentials, tokens, account data, private repository coordinates, runtime
  state, or secret-bearing fixtures.
- Preserve public source provenance in `docs/provenance.md` without carrying
  source-project policy into the portable core.
- Do not create a remote, publish, push, or open a pull request unless the user
  explicitly authorizes that external action.

## Skill index

| Task | Skill |
| :--- | :--- |
| Adopt, add, audit, refresh, or update kit content in a target | [agent-guidance-maintenance](skills/agent-guidance-maintenance/SKILL.md) |
| Inspect a target project and propose/adopt a minimal guidance set | [bootstrap-project](skills/bootstrap-project/SKILL.md) |
| Audit code, tests, docs, or guidance for evidence-backed quality defects | [ai-slop-detector](skills/ai-slop-detector/SKILL.md) |
| Review a system architecture with fresh eyes and compare options | [architecture-review](skills/architecture-review/SKILL.md) |
| Review a diff, branch, subsystem, or repository for concrete defects | [code-review](skills/code-review/SKILL.md) |
| Verify documentation against source, build, configuration, and CI truth | [documentation-review](skills/documentation-review/SKILL.md) |
| Adapt canonical guidance to a known or future agent harness | [harness-adaptation](skills/harness-adaptation/SKILL.md) |
| Diagnose an observed failure by finding its root cause before fixing it | [systematic-debugging](skills/systematic-debugging/SKILL.md) |
| Review security boundaries, authority, secrets, and sensitive data flows | [security-review](skills/security-review/SKILL.md) |
| Discover and close a bounded set of meaningful correctness gaps | [quality-hardening](skills/quality-hardening/SKILL.md) |
| Simplify or split code while preserving behavior | [reduce-code-size](skills/reduce-code-size/SKILL.md) |
| Partition independent work among bounded workers | [parallel-multi-agent](skills/parallel-multi-agent/SKILL.md) |
| Create or update a project-local skill | [skill-authoring](skills/skill-authoring/SKILL.md) |
| Measure whether a skill improves outcomes with clean-context evaluations | [skill-evaluation](skills/skill-evaluation/SKILL.md) |
| Review skill content or external candidates for useful improvements | [skill-reviewer](skills/skill-reviewer/SKILL.md) |
| Audit guidance structure, overlap, conflicts, and routing | [rules-and-skills-audit](skills/rules-and-skills-audit/SKILL.md) |
| Reduce guidance context cost without weakening behavior | [skill-optimizer](skills/skill-optimizer/SKILL.md) |

## Verification

Run from the repository root:

```text
make check
```

The check must validate every skill, run deterministic script tests, verify
relative links, lint all Markdown and MDC guidance, lint and format-check Python,
reject unfinished templates, and scan tracked content for common secret and
personal-path patterns. These checks are required before commit or push;
address findings rather than skipping the gate. Report skipped optional tooling
as skipped, never passed.
