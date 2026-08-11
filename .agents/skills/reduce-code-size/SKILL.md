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

Use [code-review](../code-review/SKILL.md) for a review without a size goal,
[ai-slop-detector](../ai-slop-detector/SKILL.md) for an evidence-based cleanup
audit, [architecture-review](../architecture-review/SKILL.md) for redesign or
boundary changes, and [quality-hardening](../quality-hardening/SKILL.md) for
correctness work whose primary goal is not reduction.

## Inputs and baseline

Take the target files or subsystem, the explicit size objective, applicable
local rules, and the source, tests, build, and lint checks that define current
behavior. Measure the relevant per-file and aggregate size before changing
anything. Record the baseline and the behavior proof available for the scope.
Size alone is an investigation trigger, not evidence that code is defective.

## Reduction workflow

1. **Confirm the target and contract.** Identify public callers, distinct test
   cases, generated or contract-owned files, and behavior that must remain
   unchanged. Stop if the request would require a semantic change.
2. **Apply the ladder in order.** Prefer deleting proven dead code, removing
   duplicate local logic, reusing an existing helper, and using established
   language idioms. Extract a helper only for multiple genuine uses and a
   cohesive reason. Change dependencies only when the verified net cost is
   lower.
3. **Split selectively.** Split a large file only by a cohesive reason to
   change and an ownership boundary that makes future work clearer. Do not
   split mechanically or move code merely to change a line count.
4. **Work in small slices.** After each cohesive slice, run the relevant
   formatter, compiler, linter, and tests before starting the next slice.
   Keep contract expectations independent from the implementation.
5. **Compare the result.** Re-measure per-file and aggregate size, confirm
   behavior and test coverage did not regress, and assess readability,
   coupling, dependency cost, and merge surface. Keep a change only when it is
   a net improvement.

## Safety and stop conditions

Never delete a distinct test, weaken an assertion, widen an exclusion, collapse
a trust boundary, or hide a warning or failure to obtain a smaller diff. A
reduction that changes error handling, retry behavior, cancellation,
idempotency, persistence, or protocol output is a behavior change: stop and
return it to the appropriate owner instead.

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
