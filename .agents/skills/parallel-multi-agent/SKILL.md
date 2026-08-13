---
name: parallel-multi-agent
description: >-
  Partition a substantial task into bounded concurrent workers with disjoint
  ownership, explicit authority, sensitive-path restrictions, compact handoffs,
  and parent-owned integration. Use when the user asks to delegate, parallelize,
  fan out, use subagents, or when authorized work contains multiple genuinely
  independent implementation or review tracks. Do not use for tiny, coupled,
  same-file, or sequential work.
---

# Parallel Multi-Agent Work

Use the active harness's native worker and model controls. The parent remains
responsible for the whole task, integration, cleanup, and final evidence.

## Contract

- **Input:** an authorized parent task with at least two independent tracks.
- **Output:** track matrix, worker briefs, compact results, integrated changes,
  and serial final verification.
- **Side effects:** only the edits and tool actions already authorized by the
  parent task. Delegation does not broaden authority.
- **Stop conditions:** no user authority to delegate; unresolved shared-file
  ownership; unavailable required capability; secret/runtime-state access;
  worker requests a material scope expansion; or integration cannot be
  verified safely.

## 1. Decide whether to delegate

Delegate only when all are true:

1. The user or applicable project guidance authorizes workers.
2. Each track has a self-contained result that materially advances the task.
3. Write scopes are disjoint, or each track is read-only with a distinct
   evidence question.
4. The parent can continue useful non-overlapping work while workers run.
5. The parent can inspect and verify every returned change.

Keep work in the parent when it is the next blocking decision, touches one hot
file, depends on an unfinished contract, is too small to justify handoff, or
requires context that cannot be bounded safely.

## 2. Build the track matrix

Use the smallest useful number of workers. Prefer one track per concern or
ownership boundary, not one worker per file.

| Track | Goal | Owns / may read | Must not touch | Risk | Capability | Depends on |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| A | concrete result | exact paths | shared or sensitive paths | low/medium/high | required tools/reasoning | none or named output |

Reserve coupled integration work for the parent. Do not give multiple editing
workers the same file or generated output directory.

## 3. Select workers honestly

- Use an exact model/provider/effort only when the harness exposes and supports
  that selection. A role or agent name is not route evidence.
- Choose capability in proportion to risk and complexity. Use a stronger or
  independent verifier for high-risk or disputed findings, not by default.
- Record requested and actual selection when the harness reports it. State
  substitutions or unknown routing plainly.
- Do not build repository-side model catalogs, pricing tables, quota probes, or
  fallback engines to imitate the host.

## 4. Brief each worker

Every brief must include:

- repository root and current branch/state;
- one concrete goal and acceptance criteria;
- exact allowed write paths and forbidden paths;
- already-completed context needed to avoid duplicate work;
- relevant project invariants and matching skill paths;
- whether the worker may edit, run tests, browse, or contact external systems;
- a compact response shape, iteration/context bound, and stop condition.

For delegated evaluation workers, keep the task blind: pass only the natural
user task and allowed fixtures, never the expected output, assertions, scoring
rubric, comparison condition, or grading assignment. Use neutral worker-visible
workspace and file names; do not encode the skill name, condition, case ID, or
evaluation purpose in paths or wrapper text. Set and verify the worker's actual
working directory before it reads files; a path mentioned in a prompt is not
isolation. Treat automatic system and tool metadata as visible: if a baseline
worker receives the target skill's name, path, description, catalog entry,
injection label, or other target-skill identity, the condition is contaminated
even if the skill text is not loaded. The parent retains the evaluation
metadata and grades the outputs after the workers finish. If discovered
`AGENTS.md` files carry the injection, use separate neutral variants: the
guided variant may name a neutral guidance path, while the baseline variant
must not mention that path or use an `if-exists` check. Capture worker logs
outside both worker roots; a worker must not be able to inspect its own trace.

Default sensitive-path denylist:

```text
.env and credential files
databases and application state
logs and diagnostics containing user data
kubeconfigs, cloud profiles, browser profiles, and keychains
home-directory files outside the named repository
unrelated worktrees and repositories
```

Pass raw artifacts and the task, not the parent's suspected answer. A worker
used for validation should be able to find a defect without leaked conclusions.

## 5. Launch concurrently

Launch independent workers in one parallel operation when the harness supports
it. Do not simulate parallelism by waiting for one independent worker before
starting the next.

While workers run, continue the parent-owned critical path. Avoid duplicating a
delegated task. Poll sparingly and only when the next parent step needs the
result.

For editing workers in build-heavy repositories, either give each an isolated
worktree or make the parent the sole owner of builds. Never trust final evidence
from overlapping builds that share caches, locks, ports, databases, or output
directories.

## 6. Integrate and verify

For every result:

1. Read the compact handoff and inspect the actual diff or evidence.
2. Reject changes outside ownership or unsupported claims.
3. Resolve cross-track conflicts in the parent; do not send the same hot files
   back to several workers.
4. Re-run affected targeted checks after integration.
5. Run final repository gates serially from the integrated state.
6. Close workers and remove only temporary state created for this fan-out.

Do not call a worker's green check the final result unless it ran against the
exact integrated state and did not overlap unsafe shared execution.

## Report

Return:

- track-to-worker/model mapping and any unknowns or substitutions;
- files or evidence owned by each track;
- integrated changes and rejected/out-of-scope results;
- targeted and final checks with pass/fail/not-run status;
- worker, worktree, process, and temporary-state cleanup status.
