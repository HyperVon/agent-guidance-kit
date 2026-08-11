# Agent operating norms

These are the small always-on rules for any coding harness working in this
repository. Task-specific procedure belongs in a matching skill.

## 1. Prefer local guidance

Read repository-local rules and matching skills before inventing a workflow.
Local guidance governs over external or global guidance; use external material
only for uncovered gaps.

## 2. Inspect before changing

Establish the repository state, relevant contracts, source of truth, and user
intent before editing. Preserve unrelated changes and do not infer permission
for commits, publication, external messages, or destructive actions.

## 3. Use the smallest applicable skill

Load only the procedure needed for the task. Extend an existing owner skill
when the boundary fits; create a new skill only for a distinct trigger and
workflow.

## 4. Prefer evidence over assumptions

Use current source, tests, build files, configuration, observed behavior, and
primary documentation as evidence. Separate observations, inferences, and
unknowns. Never invent commands, APIs, integrations, or verification results.

## 5. Keep implementations lean and contract-aware

Be defensive at real trust boundaries and confident inside validated contracts.
Avoid speculative abstractions, duplicate validation, silent fallbacks, fake
tests, and wrappers without current policy or transformation value.

## 6. Plan meaningful mutations

For guidance adoption, external content, broad rewrites, or risky changes,
present the exact scope and conflicts before applying. Approval of a plan does
not authorize unrelated operations.

## 7. Verify before completion

Run the smallest useful checks during iteration and the repository's complete
relevant gates before claiming success. State exactly what ran, what passed,
what failed, and what was not run.

## 8. Keep context and output bounded

Search narrowly, summarize large outputs, retain only actionable excerpts, and
store diagnostics outside tracked content. Do not dump secrets, dependency
trees, full logs, or unrelated files into prompts or reports.

## 9. Parallelize only independent work

Use the active harness's native worker and model-selection capabilities when
the user authorizes delegation. Give workers disjoint ownership, bounded
context, explicit stop conditions, and no secret access. A role name is not
proof of a provider or model. The parent owns integration and final checks.

## 10. Leave a clean, recoverable state

Do not leave servers, watchers, temporary files, worktrees, or child workers
running after they are no longer needed. Never share credentials or runtime
state between worktrees. Keep public tracked files free of personal and secret
data.
