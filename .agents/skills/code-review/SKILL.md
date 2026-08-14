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
`architecture-review` for redesign or refactor-versus-rewrite choices,
`ai-slop-detector` for broad artifact-quality and test-independence audits,
`documentation-review` for factual docs sync, `quality-hardening` for a bounded
set of correctness fixes, and `reduce-code-size` when the goal is size
reduction.

Freeze the review point before judging findings: record the base, diff, source
version, generated-file policy, and checks that were actually run. Review the
specification or public contract separately from engineering standards so a
style preference cannot masquerade as a correctness defect.

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

1. **Establish review truth.** Inspect `git status`, the complete scoped diff,
   merge base, and target base; identify generated files, contract boundaries,
   public interfaces, security surfaces, persistence, concurrency, and
   user-visible changes.
2. **Read the contract.** Read applicable local guidance, source-of-truth
   code/configuration, relevant tests, and documentation before evaluating
   behavior. Source and executable checks outrank stale prose.
3. **Inspect concrete risks.** Check boundary ownership, input validation,
   state transitions, error propagation, cancellation and lifecycle, retries,
   timeouts, duplicate or out-of-order work, security and secret handling,
   compatibility, and data-loss behavior as applicable. Trace changed symbols
   through callers, removed behavior, sibling implementations, and the
   canonical source of truth; do not assume a local diff is the whole contract.

   **High-risk defect categories:**
   - *Concurrency & atomicity:* unlocked mutexes/locks on early return or exception paths; check-then-act (TOCTOU) races; goroutine/thread/task leaks without lifecycle termination; unhandled promise/async task rejections.
   - *State transitions & persistence:* partial multi-step persistence writes lacking transaction rollback; missing database connection/file handle release in `finally`/`defer` blocks; idempotency failures during retries.
   - *Input & boundary validation:* missing bounds, size, or type checks on untrusted payloads; unescaped inputs reaching regex/SQL/shell parsers; sensitive data leaked into log lines.
   - *Error propagation:* swallowed exceptions returning synthetic default values that masquerade as success; missing error wrapping that loses operational root cause.
4. **Inspect tests and evidence.** Each changed test should protect a distinct
   defect class and derive expected values from a contract or independent
   oracle. Ask whether a plausible wrong implementation would fail. Run the
   smallest relevant local checks and record anything not run. Treat an
   unverified blocker as unresolved rather than a confirmed finding.
5. **Check adjacent claims.** Verify changed docs, configuration, generated
   artifacts, and integration instructions against current source. Do not
   expand into a full documentation or architecture audit without that scope.
6. **Report and stop.** Rank concrete findings, state the smallest safe
   correction, include strengths and verification gaps, then stop unless the
   user explicitly authorizes applying selected findings. Maintain one
   disposition for every finding and every uncovered review area: confirmed,
   disproved, duplicate, needs-information, waived, or carried forward.

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

### Reviewer anti-patterns to avoid

- **Style nitpicking:** Do not report formatting, identifier casing, or subjective syntax preferences if automated linters pass and the code matches local codebase conventions.
- **Speculative vulnerabilities:** Do not report security flaws without demonstrating a concrete untrusted data flow, unverified input, or reachable abuse path.
- **Scope creep & unsolicited redesign:** Do not demand an architectural rewrite when reviewing a localized bug fix or narrow feature addition.
- **Phantom verification:** Never claim tests passed or code is verified without running the exact test command and inspecting output.

Do not call a check passed when it was not run. Do not claim merge readiness,
approval, or external completion from this review alone.

Before the final verdict, check review coverage against the frozen scope and
state what was not inspected. A clean report means no evidence-backed finding
was confirmed in the examined scope; it does not mean the change is universally
safe.

## Side effects and stop conditions

Review mode is read-only. Applying findings is a separate explicitly authorized
mode and may change only the selected scope, with focused verification after
each correction. Stop when evidence is insufficient, when a proposed fix
changes architecture or behavior beyond the review request, or when the issue
belongs to a neighboring skill; report the hand-off or verification gap instead
of guessing.
