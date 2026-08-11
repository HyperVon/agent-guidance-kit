---
name: architecture-review
description: >-
  Perform a fresh-eyes, evidence-based architecture review of a repository or
  subsystem and compare meaningful Keep, Evolve, Replace, or Greenfield
  options. Use for architecture reviews, redesign questions, ADR planning, or
  refactor-versus-rewrite decisions. Recommend only; do not implement the
  recommendation in the review.
---

# Architecture Review

## Authority and boundary

This is a recommend-only review. Discover the design from current source,
configuration, tests, build behavior, and observed interfaces; treat existing
documentation and guidance as claims to verify. Do not edit application code,
start a rewrite, create external changes, or present a recommendation as an
approved implementation. A later, explicit implementation request is a
separate step.

Use this skill for system or subsystem design decisions. Hand off focused
changed-code defects to [code-review](../code-review/SKILL.md), artifact-level
quality defects to [ai-slop-detector](../ai-slop-detector/SKILL.md), factual
documentation drift to [documentation-review](../documentation-review/SKILL.md),
and behavior-preserving simplification to
[reduce-code-size](../reduce-code-size/SKILL.md). Structural guidance overlap
belongs to [rules-and-skills-audit](../rules-and-skills-audit/SKILL.md).

## Inputs and evidence

Take the named repository, subsystem, or milestone slice; the user's review
question; applicable local rules; and the relevant source, tests,
configuration, interfaces, build files, and operational evidence. If scope is
ambiguous, state the assumption and ask only when choosing the scope would
materially change the review.

Use an evidence trail for every consequential claim. Prefer current source and
tests over narrative docs or memory. Mark direct observations, inferences,
hypotheses, and unresolved assumptions separately. When evidence conflicts,
identify the conflict and explain which source is more authoritative; do not
silently average it. Before a major recommendation, identify missing evidence,
its decision impact, and the smallest validation that would close the gap.

## Workflow

1. **Frame the decision.** State the review scope, question, constraints,
   non-goals, and what would count as a meaningful improvement.
2. **Discover the as-is design.** Map entry points, components, data and
   control flows, ownership, trust and protocol boundaries, persistence,
   concurrency, configuration, and test or operational seams from source.
   Record the largest coupling clusters and what already works well.
3. **Stress-test the design.** Check domain placement, module boundaries,
   failure and recovery behavior, concurrency and lifecycle, security and
   data handling, operability, testability, build cost, and team change cost.
   Skip dimensions with no evidence of a relevant issue.
4. **Compare alternatives.** For each real problem, compare a credible
   **Keep current** option with **Evolve**, **Replace**, or **Greenfield** only
   when warranted. State impact, evidence, cost, reversibility, migration
   hazards, and a validation signal for each serious option.
5. **Filter and deliver.** Drop taste-only churn, fashionable technology
   swaps, and proposals unsupported by a concrete quality, security,
   operability, correctness, or maintainability delta. Prefer fewer, sharper
   recommendations.
6. **Stop before implementation.** Present the report and decision choices;
   wait for explicit selections before drafting an implementation plan or
   changing code.

## Output

Return a decision-oriented report with:

- executive summary and inferred constraints;
- an as-is architecture map, ownership map, and useful flow diagram when it
  improves clarity;
- keep-as-is decisions and explicit non-issues;
- findings with severity, evidence anchors, problem, options, recommendation,
  expected payoff, cost/risk, and the next validation step;
- strategic options and an ordered decision list when the scope warrants them;
- verification gaps and unresolved assumptions.

If the repository has an established decision-record location and a persistent
record is requested or required by its local workflow, write the same choices
there. Do not invent a path, format, tool, or external artifact; when no such
location exists, keep the decision record in the report.

## Severity and stop rules

- **P0:** structural risk to security, data integrity, or destructive behavior.
- **P1:** material architecture gap that breaks a contract or blocks safe,
  reliable operation or an important change.
- **P2:** meaningful improvement with clear payoff and safe deferral.
- **P3:** optional strategic polish with no demonstrated near-term impact.

Do not recommend a rewrite without evidence and a credible migration path. Stop
when the review question is answered, when alternatives have no meaningful
delta, or when a missing fact is a real blocker. Report the gap rather than
filling it with invented APIs, scale assumptions, dependencies, or tools.
