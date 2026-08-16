---
name: reduce-code-size
description: >-
  Reduce code size or split oversized files while preserving behavior,
  contracts, safety, and verification. Use when the user asks to shrink code,
  remove redundant implementation, reduce LOC, or make a behavior-preserving
  refactor. Measure first and stop when the reduction is not a net win.
---

# Reduce Code Size

## Authority and boundary

This skill is edit-capable only for an explicit request to reduce code size or
perform the corresponding behavior-preserving refactor. Without that request,
inspect and report; do not edit. Work only in the requested scope. Preserve
public behavior, interfaces, wire formats, security boundaries, error
semantics, retries, idempotency, and distinct tests.

Use `code-review` for a review without a size goal, `ai-slop-detector` for an
evidence-based cleanup audit, `architecture-review` for redesign or boundary
changes, and `quality-hardening` for correctness work whose primary goal is not
reduction.

## Inputs and baseline

Take the target files or subsystem, the explicit size objective, applicable
local rules, and the source, tests, build, and lint checks that define current
behavior. Measure the relevant per-file and aggregate size before changing
anything. Record the baseline and the behavior proof available for the scope.
Size alone is an investigation trigger, not evidence that code is defective.

## Reduction workflow

1. **Confirm the target and contract.** Identify public callers, distinct test
   cases, generated or contract-owned files, and behavior that must remain
   unchanged. Write a scope allowlist and behavior-parity checklist, and stop
   if the request would require a semantic change.

   **Verify dynamic usage before removal:**
   - Check serialization schemas (e.g., Pydantic models, dataclasses, ORM entities, protobuf/JSON serializers) where fields are accessed dynamically.
   - Check kwargs forwarding (`**kwargs`), dependency injection containers, and reflection/metaclass lookups (`getattr`, `__dict__`).
   - Check public plugin or event handler entrypoints registered via string names or decorators.
2. **Apply the ladder in order.** Prefer deleting proven dead code, removing
   duplicate local logic, reusing an existing helper, and using established
   language idioms. Extract a helper only for multiple genuine uses and a
   cohesive reason.

   **Avoid the cross-domain DRY trap:**
   Do not unify superficially similar code if the components belong to different business domains or have different reasons to change. Extract a shared helper only when the logic represents a genuinely reusable, cohesive utility with a single clear owner. Change dependencies only when the verified net cost is lower.
3. **Split selectively.** Split a large file only by a cohesive reason to
   change and an ownership boundary that makes future work clearer. Do not
   split mechanically or move code merely to change a line count.
4. **Work in small slices.** After each cohesive slice, record a checkpoint
   containing changed paths, the remaining allowlist, behavior risks, and
   verification evidence. Run the project's full behavior gate for the affected
   scope (formatter, compiler, linter, and the complete test suite / coverage
   for touched and dependent modules), not only a subset of relevant tests,
   before starting the next slice. Keep contract expectations independent
   from the implementation and preserve a handoff if the work must pause.
5. **Compare the result.** Re-measure per-file and aggregate size, confirm
   behavior and test coverage did not regress, and assess readability,
   coupling, dependency cost, and merge surface. Keep a change only when it is
   a net improvement.

## Safety and stop conditions

### Reject code golfing and false compression

Never reduce line count at the expense of readability, maintainability, or error clarity. Specifically reject:

- Replacing clean `if/else` control flow with deeply nested ternary expressions or boolean short-circuit hacks.
- Replacing readable data manipulation with impenetrable regexes or multi-stage chained lambdas.
- Collapsing explicit error checks or distinct error messages into a single generic handler just to save lines.
- Omitting type annotations, docstrings, or clarifying comments to artificially deflate file size.

True size reduction removes dead code, eliminates duplicate implementations, simplifies bloated abstractions, and leverages standard language features—it never obfuscates logic.

Never delete a distinct test, weaken an assertion, widen an exclusion, collapse
a trust boundary, or hide a warning or failure to obtain a smaller diff. A
reduction that changes error handling, retry behavior, cancellation,
idempotency, persistence, or protocol output is a behavior change: stop and
return it to the appropriate owner instead.

Preserve git blame hygiene: Avoid purely cosmetic reordering of functions or moving files across directories unless the split aligns with an established ownership boundary. Keep changes targeted to minimize merge friction on active branches.

Do not resolve a size-only review finding by citing a line-count reduction.
Each retained slice needs behavior-parity evidence, and an explicit waiver is
preferable to an unverified reduction when a contract or generated source is
out of scope.

Stop when a relevant check fails, behavior cannot be proven, the change adds
more abstraction or coupling than it removes, the size objective is met, or
the next ladder step is not a net win. Preserve the work up to the last
verified slice and report the stopped point and remaining uncertainty.

## Output and side effects

Return a reduction report containing the target and objective, before-to-after
size measurements, changes by ladder step, behavior and verification evidence,
test-count or coverage comparison when available, remaining risks, and any
deferred reduction. Authorized work may edit only the requested source scope;
it must not commit, publish, or alter unrelated files. If no safe reduction is
found, return the baseline and evidence rather than forcing a change.
