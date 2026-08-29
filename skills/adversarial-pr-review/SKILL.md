---
name: adversarial-pr-review
description: >-
  Parent-validated adaptive adversarial PR review — requires a fresh,
  independent read-only subagent, partitions larger diffs into bounded tracks,
  and re-reviews affected tracks until convergence. Use when the user
  explicitly requests an adversarial or multi-agent review, or when the target
  repository policy explicitly requires adversarial review before publication.
---

# Adversarial PR Review

A routeable, opt-in review workflow. The portable kit does not automatically
require this review for every PR — use this skill only when the request or the
adopting repository's own policy says to do so. Whenever invoked, it requires
at least one fresh, independent read-only subagent; parent-only self-review is
not a valid substitute. Adopting projects may make it mandatory locally by
documenting that policy and invoking this skill from their
`git-github-workflow` or `AGENTS.md`.

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

This skill is opt-in by default. A target repository may make the adversarial
review gate mandatory by adopting it in its own `AGENTS.md` policy; otherwise it
remains opt-in unless the local policy adopts it.

## Core operating model

- **Parent owns integration and validation.** Workers are bounded, read-only
  reviewers with disjoint file ownership — not editors, mergers, or publishers.
- **Fresh-context independence.** At least one reviewer must run in a newly
  initialized subagent context with no parent conclusions or prior review
  output. The parent must launch that reviewer; the reviewer is not expected
  or permitted to recursively launch another reviewer. If the parent cannot
  provide that capability, the review is blocked.
- **Adaptive and convergent.** Only tracks with findings are re-reviewed after
  authorized fixes, using a fresh subagent context each time. The gate is not
  complete until the final pass reports no additional findings.
- **Read-only workers, parent-owned integration.** Workers return findings;
  the parent validates, de-duplicates, ranks, and integrates.
- **No external publication.** Workers do not push, merge, approve, or post
  external comments.
- **Approval and delegation consistent with `parallel-multi-agent` and applicable
  repository-local operating guidance, when present.** Delegation requires user
  or repository-policy authorization to use workers, disjoint ownership, and
  parent-owned integration and final verification. Do not invent an additional
  approval gate for routine PRs merely because this skill exists in the catalog.

## Track matrix

Build the smallest useful set of tracks for the PR (usually 2–6, max 8); a
small change may use one coupled track. Partition by ownership or risk, not
one-per-file. Reserve a coupled track when files must be reasoned about
together. Every track must be assigned to the fresh read-only subagent; the
parent cannot substitute for the review.

| Track | Owns (files or dirs) | Risk | Depends on |
| :---- | :------------------- | :--- | :--------- |
| A | … | high/medium/low | none |
| B | … | … | none |

For review work, also record iteration cap and stop condition per track.
Document the matrix and obtain approval before the first parallel worker
launch unless the user explicitly requested this workflow or applicable
repository policy already authorizes it. A routine PR does not implicitly require
this extra approval unless the repository has adopted the policy above.

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
3. **Delegate bounded review in fresh context.** Each worker reviews only its
   assigned paths and minimum dependencies, grounding every finding in a path
   and line, failing check, contract, or reproducible risk. Do not provide the
   worker with the parent's suspected findings or conclusions.
4. **Parent validation and deduplication.** Before reporting, the parent independently verifies each candidate finding against the diff and codebase:
   - *Line anchor check:* Verify that the referenced line and code snippet match HEAD/merge-base diff.
   - *Reachability check:* Verify whether caller context, type definitions, or upstream middleware already neutralize the alleged defect.
   - *Contract verification:* Reject findings based on personal style or ungrounded assumptions; require a concrete failing scenario or violated invariant.
   - *Intentional contract-change check:* Treat a PR description, issue, or
     comment as evidence of intent, not by itself as proof of authorization or
     correctness. Determine whether a breaking change or deprecation is explicitly
     within user- or repository-approved scope and consistent with the repository's
     source-of-truth contract and versioning policy. Even when intentional, verify
     affected callers and consumers, migration or compatibility handling, tests and
     documentation, release implications, and rollback or recovery. Retain the
     finding when authorization is unclear or migration evidence is incomplete;
     when the change is authorized and fully accounted for, reject the alleged
     accidental-regression finding with those anchors.
   - *Deduplication:* Merge duplicate findings across track boundaries into a single anchored item with primary ownership.
5. **Report and stop (Review Phase).** Return review scope, track matrix,
   per-track verdicts, and ranked findings anchored to `path:line` with
   severity and concrete impact. Stop and wait for explicit user approval
   before applying any fixes. Do not publish until the fresh-context gate has
   converged.
6. **Iterative fix and re-review (when authorized).** If and only if the user explicitly authorizes applying corrections:
   - Apply minimal safe fixes in the parent workspace for authorized findings.
   - Re-dispatch only the specific worker tracks whose assigned files or direct dependencies were modified, using a newly initialized context. Unaffected tracks are not re-run.
   - Enforce an iteration cap (default: maximum 3 cycles). The final pass must report no additional findings; if findings persist, stop and report the remaining delta rather than publishing.

## Boundaries and stop conditions

- Keep integration and validation in the parent when the change touches one
  hot file, is too small for multiple tracks, or track ownership cannot be made
  disjoint; do not use that as permission to replace the required fresh
  subagent review.
- Do not edit, commit, push, merge, or publish from workers.
- Parent-only self-review is invalid. Stop and report a blocked review when a
  fresh read-only subagent cannot be launched or cannot return an independent
  verdict.
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
