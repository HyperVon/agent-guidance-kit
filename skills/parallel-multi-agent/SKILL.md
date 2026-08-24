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
6. Workers must not recursively delegate or spawn child subagents unless the parent brief explicitly assigns a hierarchical coordinator role.

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

- Treat manifest + lockfile pairs as implicit shared state even when workers edit disjoint source. A dependency add or install in any track rewrites the lockfile. Make lockfile regeneration a parent-owned serial step: let workers finish, then run the single package-manager update/regenerate in the integrated state and review the diff.

### Freeze the fan-out base

Before launching editing workers, record one integration-base commit SHA and
the parent's working-tree state.

- Start independent editing work from that same committed base whenever the
  harness/worktree model permits it.
- Do not let one worker merge, rebase, cherry-pick, or otherwise consume a
  sibling worker's unpublished changes; sibling tracks must remain independent
  unless the track matrix explicitly declares a dependency.
- If the parent advances shared contracts while workers are active, mark
  affected worker results stale and revalidate them against the new contract.
- A disjoint file set does not prove semantic independence. Treat schemas,
  public interfaces, generated contracts, registries, shared configuration,
  and cross-file invariants as shared integration state even when the physical
  write paths do not overlap.
- Record the base SHA in each editing-worker brief and compare the returned
  result against that base before accepting it.

Integrate dependent tracks in declared dependency order, then run final
verification only from the fully integrated state.

## 3. Select workers honestly

- Use an exact model/provider/effort only when the harness exposes and supports
  that selection. A role or agent name is not route evidence.
- Choose capability in proportion to risk and complexity. Use a stronger or
  independent verifier for high-risk or disputed findings, not by default.
- Record requested and actual selection when the harness reports it. State
  substitutions or unknown routing plainly.
- Do not build repository-side model catalogs, pricing tables, quota probes, or
  fallback engines to imitate the host.
- When a subagent candidate's model/provider must be selected, use the harness's native selection controls rather than building a local catalog.

## 4. Brief each worker

Every brief must include:

- repository root and current branch/state;
- one concrete goal and acceptance criteria;
- exact allowed write paths and forbidden paths;
- already-completed context needed to avoid duplicate work;
- relevant project invariants and matching skill paths;
- whether the worker may edit, run tests, browse, or contact external systems;
- a compact response shape, iteration/context bound, and stop condition.

### Compact handoff contract

Instruct workers to return only a compact handoff structure (never full file contents, raw logs, or giant tool traces):

```text
Track: <Track ID/Name>
Status: SUCCESS | FAILED | PARTIAL
Modified files: <list of exact repo-relative paths>
Summary: <2-3 sentence summary of changes made>
Self-verification: <commands executed and PASS/FAIL status with counts>
Risks/Blockers: <any residual risk or deferred work, or "none">
```

For delegated evaluation workers, the deep isolation, blindness, baseline
isolation, contamination, and grading rules are owned by the
[separate evaluation repository](https://github.com/HyperVon/agent-guidance-kit-evals).
Follow those constraints and do not reimplement or weaken them here.

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
directories. Do not allow concurrent editing workers to execute tests that bind to fixed singleton resources (e.g., fixed localhost ports `:8080`, hardcoded temporary database paths in `/tmp`, fixed Docker container names, or shared `.coverage` files). Configure ephemeral resources with unique per-track IDs/randomized ports or restrict test execution to the serial parent integration phase.

## 6. Integrate and verify

### Worker failure and partial triage

When a worker hangs, times out, hits a context/iteration limit, or returns a broken patch:

1. **Isolate the failure:** Check whether the failed worker's write scope is strictly disjoint from other completed tracks. Never discard independent successful tracks due to an isolated sibling failure.
2. **Verify partial state is clean:** Before integrating any results, confirm that `PARTIAL` or `FAILED` workers' modifications are fully reverted, stashed, or isolated in a separate branch or worktree. Do not integrate green tracks on top of uncommitted partial changes from a failed sibling.
3. **Integrate green tracks:** Apply and verify the results of all successful disjoint tracks following normal verification gates.
   - For worktree-based tracks, integrate by merging or cherry-picking the track branch into the parent integration branch, then verify; only after the final serial gate passes, delete the worktree (`git worktree remove`) and the temporary track branch. Report each worktree/branch removed.
4. **Triage the failed track:** Choose one explicit recovery strategy:
   - *Re-brief with tighter scope:* If the failure was due to context overflow or ambiguous instructions, re-launch a single worker with a narrower boundary and explicit stop condition.
   - *Fall back to serial parent execution:* If the track requires sensitive context, complex integration, or debugging, execute the remaining track directly in the parent.
   - *Roll back cleanly:* If the failed track represents a blocking hard dependency for other tracks, revert temporary changes created for that track and document the blocker.

For every result:

1. Read the compact handoff and inspect the actual diff or evidence.
2. Reject changes outside ownership or unsupported claims.
3. Resolve cross-track conflicts in the parent; do not send the same hot files
   back to several workers.
4. Re-run affected targeted checks after integration.
5. Run final repository gates serially from the integrated state.
6. Close workers and remove only temporary state created for this fan-out.
7. If the final gate fails, stop and report the failure before cleanup: revert
   or stash the failed integration, then close workers and remove only the
   temporary state created for this fan-out. Do not leave a worker, worktree,
   or process running after a failed integration.

Do not call a worker's green check the final result unless it ran against the
exact integrated state and did not overlap unsafe shared execution.

## Report

Return:

- track-to-worker/model mapping and any unknowns or substitutions;
- files or evidence owned by each track;
- integrated changes and rejected/out-of-scope results;
- targeted and final checks with pass/fail/not-run status;
- worker, worktree, process, and temporary-state cleanup status.
