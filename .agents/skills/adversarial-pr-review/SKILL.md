---
name: adversarial-pr-review
description: >-
  Parent-orchestrated adaptive adversarial PR review — partitions a PR diff
  into bounded read-only reviewer tracks by file ownership and risk, validates
  findings in the parent, and re-reviews only affected tracks until
  convergence. Use when the user explicitly requests an adversarial or
  multi-agent review, or when the target repository policy explicitly requires
  adversarial review before publication.
---

# Adversarial PR Review

A routeable, opt-in review workflow. The portable kit does not automatically
require a multi-agent review for every PR — use this skill only when the
request or the adopting repository's own policy says to do so. Adopting
projects may make it mandatory locally by documenting that policy and invoking
this skill from their `git-github-workflow` or `AGENTS.md`.

## When to use this skill

Use this skill when one of these is true:

1. **Explicit request** — the user asks for an adversarial, multi-agent, or
   multi-model review of a PR or branch diff.
2. **Repository policy** — the target repository's local policy (for example
   its `AGENTS.md`, `CONTRIBUTING.md`, or `git-github-workflow` guidance)
   explicitly requires an adversarial review before publication. That local
   policy is the authority — not the mere presence of this skill in the
   portable catalog.

For ordinary PR creation or updates without either trigger, continue through
`git-github-workflow` without automatically requiring multi-agent review.
When the branch has no open PR and the user is only committing WIP without
opening one, skip unless explicitly requested.

## Core operating model

- **Parent owns the whole review.** Workers are bounded, read-only reviewers
  with disjoint file ownership — not editors, mergers, or publishers.
- **Adaptive and convergent.** Only tracks with findings are re-reviewed after
  fixes; unchanged tracks are not revisited.
- **Read-only workers, parent-owned integration.** Workers return findings;
  the parent validates, de-duplicates, ranks, and integrates.
- **No external publication.** Workers do not push, merge, approve, or post
  external comments.
- **Approval and delegation consistent with `parallel-multi-agent` and `.agents/OPERATING.md`.** Delegation requires user or repository-policy authorization to use workers, disjoint ownership, and parent-owned integration and final verification. Do not invent an additional approval gate for routine PRs merely because this skill exists in the catalog.

## Track matrix

Build the smallest useful set of tracks for the PR (usually 2–6, max 8).
Partition by ownership or risk, not one-per-file. Reserve a coupled track
when files must be reasoned about together.

| Track | Owns (files or dirs) | Risk | Depends on |
| :---- | :------------------- | :--- | :--------- |
| A | … | high/medium/low | none |
| B | … | … | none |

For review work, also record iteration cap and stop condition per track.
Document the matrix and obtain approval before the first parallel worker
launch unless the user explicitly requested this workflow. Approval of the
track matrix is proposal-first per `.agents/OPERATING.md` — a routine PR does
not implicitly require this extra approval unless the repository has adopted
the policy above.

## Adversarial inspection lenses

When delegating track scopes, assign each worker a concrete adversarial lens based on track risk:

- **Boundary & Exploit Lens:** Test for unvalidated input boundaries, path traversal, injection, unauthorized state mutation, missing rate limits, and unauthenticated side-effects.
- **Failure & Silent Corruption Lens:** Hunt for swallowed exceptions, fallback defaults that mask upstream errors, unlogged catch blocks, and missing rollback logic on partial failures.
- **State & Concurrency Lens:** Inspect shared mutable state, race conditions, TOCTOU vulnerabilities, unhandled async task cancellations, and database transaction isolation leaks.
- **False-Confidence & Slop Lens:** Challenge tests that assert only mock interactions, tautological assertions, tests missing assertion statements, or tests that pass regardless of broken contract logic.

## Workflow

1. **Establish review truth.** Inspect `git status`, the complete diff,
   merge base, and PR base branch. Read local rules and the source-of-truth
   contracts, configuration, and tests that define the changed behavior.
2. **Partition.** Assign disjoint scopes to workers. Ensure no write scope
   overlaps; read-only workers may share a file only with distinct evidence
   questions.
3. **Delegate bounded review.** Each worker reviews only its assigned paths
   and minimum dependencies, grounding every finding in a path and line,
   failing check, contract, or reproducible risk.
4. **Parent validation and deduplication.** Before reporting, the parent independently verifies each candidate finding against the diff and codebase:
   - *Line anchor check:* Verify that the referenced line and code snippet match HEAD/merge-base diff.
   - *Reachability check:* Verify whether caller context, type definitions, or upstream middleware already neutralize the alleged defect.
   - *Contract verification:* Reject findings based on personal style or ungrounded assumptions; require a concrete failing scenario or violated invariant.
   - *Deduplication:* Merge duplicate findings across track boundaries into a single anchored item with primary ownership.
5. **Report and stop (Review Phase).** Return review scope, track matrix, per-track verdicts, and ranked findings anchored to `path:line` with severity and concrete impact. Stop and wait for explicit user approval before applying any fixes.
6. **Iterative fix and re-review (when authorized).** If and only if the user explicitly authorizes applying corrections:
   - Apply minimal safe fixes in the parent workspace for authorized findings.
   - Re-dispatch only the specific worker tracks whose assigned files or direct dependencies were modified. Unaffected tracks are not re-run.
   - Enforce an iteration cap (default: maximum 3 cycles). If unresolved findings persist after 3 cycles, stop and report the remaining delta.

## Boundaries and stop conditions

- Keep work in the parent when the change touches one hot file, is too small
  to justify delegation, or track ownership cannot be made disjoint.
- Do not edit, commit, push, merge, or publish from workers.
- Stop and report when evidence is insufficient, when a proposed fix would
  change architecture or behavior beyond the review request, or when the next
  step needs credentials or external access.
- Do not treat the catalog presence of this skill as an implicit requirement
  for every PR. Ordinary PRs without an explicit request or local policy
  remain on `git-github-workflow`.

## Relationship to neighboring skills

| Skill | Owns |
| :---- | :---- |
| **adversarial-pr-review** (this) | Bounded concurrent adversarial review when explicitly requested or required by local policy |
| `code-review` | Focused single-reviewer review of a diff or subsystem |
| `git-github-workflow` | Branch, commit, PR creation, and push hygiene (adopting projects may invoke this skill from there when they want it mandatory) |
| `parallel-multi-agent` | Generic bounded parallel implementation or review work when the harness and repository policy authorize delegation |
| `ai-slop-detector` | Broad artifact-quality and test-independence audit |
| `security-review` | Security boundary, secret, and authority deep review |

Use one owner skill when it fully covers the request. Combine only when the
PR materially touches a neighboring concern. Routine PRs without an explicit
adversarial-review trigger should not incur an extra approval or delegation
step.
