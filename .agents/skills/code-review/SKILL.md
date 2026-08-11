---
name: code-review
description: >-
  Perform an evidence-based review of a diff, branch, subsystem, or repository
  for concrete correctness, contract, security, runtime, boundary, test, and
  documentation defects. Use for code reviews and change-set readiness
  feedback. Report findings first; edit only when the user separately and
  explicitly asks to apply selected findings.
---

# Code Review

## Authority and boundary

This skill produces a recommendation-first review, not an automatic refactor,
merge, publication, or approval. Do not edit reviewed files unless the user
explicitly requests application of selected findings. Keep review findings
separate from implementation decisions.

Use this skill for a focused diff or subsystem and its concrete behavior. Use
[architecture-review](../architecture-review/SKILL.md) for redesign or
refactor-versus-rewrite choices, [ai-slop-detector](../ai-slop-detector/SKILL.md)
for broad artifact-quality and test-independence audits,
[documentation-review](../documentation-review/SKILL.md) for factual docs
sync, [quality-hardening](../quality-hardening/SKILL.md) for a bounded set of
correctness fixes, and [reduce-code-size](../reduce-code-size/SKILL.md) when
the goal is size reduction.

## Inputs and evidence

Take the named diff, branch, subsystem, or repository; the review question;
local rules; and relevant source-of-truth contracts, configuration, tests,
build files, documentation, and runtime evidence. Establish the complete
changed surface before judging an individual line. If a merge base or
comparison target is named, include it in the review context.

Ground each finding in a path and line or other precise anchor, a failing check
or reproduction, a verified contract, a plausible wrong behavior, or a
distinct test gap. Separate observed facts from inferences and unknowns. Do
not treat style, size, familiarity, or suspected authorship as a defect by
itself.

## Review workflow

1. **Establish review truth.** Inspect status and the complete scoped diff;
   identify generated files, contract boundaries, public interfaces, security
   surfaces, persistence, concurrency, and user-visible changes.
2. **Read the contract.** Read applicable local guidance, source-of-truth
   code/configuration, relevant tests, and documentation before evaluating
   behavior. Source and executable checks outrank stale prose.
3. **Inspect concrete risks.** Check boundary ownership, input validation,
   state transitions, error propagation, cancellation and lifecycle, retries,
   timeouts, duplicate or out-of-order work, security and secret handling,
   compatibility, and data-loss behavior as applicable.
4. **Inspect tests and evidence.** Each changed test should protect a distinct
   defect class and derive expected values from a contract or independent
   oracle. Ask whether a plausible wrong implementation would fail. Run the
   smallest relevant local checks and record anything not run.
5. **Check adjacent claims.** Verify changed docs, configuration, generated
   artifacts, and integration instructions against current source. Do not
   expand into a full documentation or architecture audit without that scope.
6. **Report and stop.** Rank concrete findings, state the smallest safe
   correction, include strengths and verification gaps, then stop unless the
   user explicitly authorizes applying selected findings.

## Findings and severity

Return a report with scope, verdict, strengths or non-issues, findings, impact,
smallest safe correction, verification gaps, and deferred questions. Each
finding should include a severity and precise evidence anchor.

- **P0:** acceptance, security, integrity, destructive-action, or data-loss
  blocker.
- **P1:** material correctness, contract, compatibility, lifecycle, or
  boundary defect.
- **P2:** localized maintainability, documentation, or meaningful test-quality
  issue.
- **P3:** low-risk improvement without demonstrated correctness or safety
  impact.

Do not call a check passed when it was not run. Do not claim merge readiness,
approval, or external completion from this review alone.

## Side effects and stop conditions

Review mode is read-only. Applying findings is a separate explicitly authorized
mode and may change only the selected scope, with focused verification after
each correction. Stop when evidence is insufficient, when a proposed fix
changes architecture or behavior beyond the review request, or when the issue
belongs to a neighboring skill; report the hand-off or verification gap instead
of guessing.
