---
name: adversarial-pr-review
description: >-
  Parent-orchestrated adaptive adversarial PR review — partitions a PR diff
  into bounded read-only reviewer tracks by file ownership and risk, validates
  findings in the parent, and re-reviews only affected tracks until
  convergence. Use when opening a PR, updating a branch with an open PR, or
  when the user explicitly requests an adversarial or multi-agent review.
---

# Adversarial PR Review

Run inside the current agent session before finishing any PR creation or
update that will be visible on GitHub. A bare `git push` does not run it
unless the branch already has an open PR.

## When this skill is mandatory

Read and follow this skill before finishing:

1. **Open PR** — after quality gates, before `gh pr create` (see
   `git-github-workflow`).
2. **Update open PR** — when the next push will update a branch that already
   has an open PR.
3. **Explicit ask** — when the user requests adversarial, multi-agent, or
   multi-model review of a PR or branch diff.

If the branch has no open PR and the user is only committing WIP without
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
launch unless the user explicitly requested this workflow.

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
4. **Parent validation.** De-duplicate, reject ungrounded claims, and rank
   by impact (security/data-loss > correctness/contract > test/maintainability).
5. **Fix and re-review.** Apply approved corrections, then re-run only the
   affected tracks. Repeat until all tracks report no actionable findings or
   the iteration cap is reached.
6. **Report.** Return scope, matrix, per-track verdicts, ranked findings
   with anchors, strengths, verification gaps, and deferred questions. Stop
   unless the user explicitly authorizes applying selected findings.

## Boundaries and stop conditions

- Keep work in the parent when the change touches one hot file, is too small
  to justify delegation, or track ownership cannot be made disjoint.
- Do not edit, commit, push, merge, or publish from workers.
- Stop and report when evidence is insufficient, when a proposed fix would
  change architecture or behavior beyond the review request, or when the next
  step needs credentials or external access.

## Relationship to neighboring skills

| Skill | Owns |
| :---- | :---- |
| **adversarial-pr-review** (this) | Bounded concurrent review before PR creation or update |
| `code-review` | Focused single-reviewer review of a diff or subsystem |
| `git-github-workflow` | Branch, commit, PR creation, and push hygiene |
| `ai-slop-detector` | Broad artifact-quality and test-independence audit |
| `security-review` | Security boundary, secret, and authority deep review |

Use one owner skill when it fully covers the request. Combine only when the
PR materially touches a neighboring concern.
