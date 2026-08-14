---
name: quality-hardening
description: >-
  Run a bounded evidence-first QA loop: establish a baseline, find meaningful
  correctness gaps, add regression coverage tests first, make minimal fixes,
  and re-run the relevant gates. Use for test hardening, QA cycles, coverage
  gaps, edge cases, flaky behavior, or regression prevention across stacks.
---

# Quality Hardening

Harden correctness through a bounded baseline → discover → test → fix → verify
loop. This skill owns tests, regressions, and correctness evidence; it does not
own documentation synchronization, product polish, architecture redesign,
deployment, or remote-system mutations.

## Authority and source of truth

Separate intended behavior from observed behavior:

1. The user's request and repository-local rules define scope, permissions,
   risk, and approval gates.
2. Current requirements, contracts, invariants, security rules, and approved
   design define intended behavior.
3. Current code, runtime observations, failures, and diagnostics establish
   observed behavior and defect evidence.
4. Existing tests and coverage reports are evidence of what is checked, not
   proof that the behavior is correct. Do not change an assertion merely to
   preserve a buggy implementation or inflate a coverage number.

When intent and implementation disagree, name the conflict and preserve a
regression test for the defect while the production change is gated. Treat
external services, production data, credentials, and live systems as out of
scope unless the user explicitly authorizes a safe, bounded check.

## QA loop

1. **Baseline.** Inspect the working-tree scope and relevant local guidance.
   Read an existing quality backlog if the repository has one. Run the smallest
   relevant baseline checks before changing tests or code and record failures,
   skips, versions, and test counts.
2. **Discover.** Review the changed surface and nearby contracts. Deliberately
   probe boundaries, empty/null input, failures and recovery, retries and
   timeouts, ordering and concurrency, idempotence, persistence, and mode
   combinations when applicable. Prefer one sharp assertion over snapshot soup.
   Test public seams with an independent oracle; avoid assertions that merely
   restate the implementation or pass for a plausible wrong result.

   **Mock contract fidelity:**
   Prefer testing against real public seams and in-memory fakes over deep mock hierarchies:
   - Never mock the unit under test or its immediate contract boundary to make a regression test pass.
   - Do not assert only that a mock method was called (`mock.assert_called_once()`); assert the observable state, returned value, or protocol side effect.
   - When mocking external boundaries (e.g. HTTP APIs, cloud storage, payment gateways), ensure the mock accurately reproduces error codes, headers, and failure payloads observed in production.
3. **Classify.** Give every finding a stable ID, severity, size, affected path,
   expected behavior, observed behavior, and evidence anchor.
4. **Test first.** For a defect or missing guarantee, add a deterministic
   failing regression test that names the risk and reproduces it. Then make the
   smallest production fix, keep the test, and refactor only when needed for
   clarity. Do not weaken thresholds, delete coverage, or add impossible cases
   solely to make a gate green. Before a legacy refactor, add characterization
   coverage for behavior that must remain stable. Consider property-based or
   mutation testing when example tests could remain tautological; choose the
   cheapest probe that can distinguish the likely wrong behavior.

   **Flakiness and timing anti-patterns:**
   Never resolve a flaky test or race condition by adding arbitrary `sleep()` delays, bumping timeout thresholds, or reordering tests until they happen to pass. Harden timing and concurrency defects deterministically:
   - Use condition-based polling with bounded timeout intervals rather than fixed sleep delays.
   - Use explicit synchronization primitives (events, latches, promises, channels) instead of timing assumptions.
   - Inject deterministic clocks/schedulers or mock timers when testing time-dependent logic.
   - Isolate test state (databases, directories, ports) so tests do not interfere when executed concurrently or out of order.

   **Surgical fix boundary:**
   Keep the production fix surgical: The fix must be the smallest necessary change that makes the deterministic regression test pass. Do not entangle bug fixes with stylistic cleanup, signature refactoring, or unrelated optimizations in the same hardening slice.
5. **Verify.** Re-run the focused test, then the relevant repository gates. If
   caching could hide the change, force re-execution. Check test-result files,
   counts, failures, skips, coverage, generated contracts, and other artifacts
   that the gate claims to validate. Run manual or visual checks when the
   changed behavior cannot be established by automation.

   **Test isolation verification:**
   Verify that a newly added test passes both in isolation AND when executed as part of the full test suite (or in randomized test order). Confirm that fixtures cleanly tear down modified environment variables, monkeypatches, database state, and open file descriptors.

   Record confidence per meaningful behavior, not only a global percentage;
   fresh evidence must include the original reproduction and the relevant
   changed boundary.
6. **Stop.** Stop when the bounded slice is green, no actionable finding
   remains, required approval is pending, or a required check is blocked. Do
   not turn a QA pass into an unapproved feature or redesign.

## Approval gate

Use the repository's size labels when they exist; otherwise use these defaults:

- **S** — One deterministic regression test, isolated test-only coverage, or an
  obvious low-impact fix. Apply only inside the user's explicit scope and
  report it.
- **M** — Multiple tests or files, a module-level fix, changed public behavior,
  a broadened gate, or a new test-harness path. Present the exact plan, files,
  risk, and verification; wait for explicit approval.
- **High-risk** — Security/auth, privacy, data loss or migration, concurrency,
  compatibility contracts, financial or safety behavior, production
  configuration, deployment, or external side effects. Stop for explicit
  approval regardless of size and include rollback or compensating checks.

Test-only coverage may proceed as S/M when it does not change production
behavior; a production fix exposed by that test follows the applicable M or
high-risk gate. Do not create or modify issues, pull requests, releases,
deployments, or other remote state automatically.

## Completion contract

Return this report, with no empty or implied fields:

```text
Quality hardening
Scope: <paths, behavior, and risk boundary>
Baseline: <exact checks; PASS|FAIL|SKIPPED|BLOCKED; counts and first failure>
Findings: <ID, size/severity, expected vs observed, evidence path:line/test>
Changes: <tests first, fixes second; exact paths and purpose>
Verification:
  - <focused test/check> — PASS|FAIL|SKIPPED|BLOCKED; <result/counts>
  - <relevant full gate> — PASS|FAIL|SKIPPED|BLOCKED; <result/counts/artifact>
Residual risk or deferred approval: <item and reason, or "none">
Changed paths: <exact paths>
```

A passing command without the relevant count or artifact is incomplete evidence.
Report optional checks as `SKIPPED`, required unavailable checks as `BLOCKED`,
and failures with the first actionable cause. Do not claim completion until the
focused regression and every applicable final gate have been accounted for.
