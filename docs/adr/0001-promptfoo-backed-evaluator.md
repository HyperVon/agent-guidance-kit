# ADR-0001: Promptfoo-backed evaluator — GO WITH MATERIAL GAPS

- **Status:** accepted
- **Decision date:** 2026-08-23
- **Deciders:** AGK maintainer
- **Primary document:** [evidence-evaluator-architecture.md](../evaluations/evidence-evaluator-architecture.md)
- **Milestone tracker:** [evidence-evaluator-milestones.md](../evaluations/evidence-evaluator-milestones.md)
- **Historical M1 evidence:** [`../evaluations/promptfoo-spike/M1-REPORT.md`](../evaluations/promptfoo-spike/M1-REPORT.md)

## Context

The completed Promptfoo compatibility spike (branch `spike/promptfoo-compat`,
evidence commit `217d53f5db7ea01d4fd4fadbefdfe987f663cbb6`) produced
`REPORT.md`, a v1/v2 comparison, passing tests, and a fresh-context adversarial
review. The architecture document
(`docs/evaluations/evidence-evaluator-architecture.md`) is already merged into
`main` at `bfbd03d3f655c97a063dd945f2ee254f0b57e01d`.

The question this ADR answers:

> Should AGK proceed toward migrating its evaluation engine to Promptfoo, given
> the spike evidence?

## Decision

**GO WITH MATERIAL GAPS.**

Promptfoo 0.122.0 demonstrated sufficient replacement of AGK's commodity
evaluation mechanics — model invocation orchestration, repetition handling,
assertion execution, structured result export, side-by-side experiment
organization, caching control, and candidate/reference comparison structure —
while AGK-specific experimental semantics (corpus projection, routing metrics,
baseline fairness, Layer A/B/C gating, holdout discipline, provenance, workspace
controls, Kilo integration) remain in thin custom code.

The existing evaluator v1 remains intact and the spike was **not** merged into
`main`.

### Selected direction

- Use Promptfoo as the commodity evaluation engine.
- Initially pin the validated version: `0.122.0`. Future upgrades must be
  verified by deterministic integration/parity tests.
- Create a new `agent-guidance-kit-evals` repository to own the canonical AGK
  corpus, methodology, thin Promptfoo integrations, provenance, and historical
  evidence.

### Dependency direction

```text
agent-guidance-kit-evals
        |
        v
external agent-guidance-kit target
        |
        v
     Promptfoo
```

AGK must remain independently usable; it must not depend on the eval repository
or Promptfoo.

## Material gaps

| Gap | Risk | M-stage owner | Acceptance criterion |
| --- | --- | --- | --- |
| Semantic judge instability | Incorrect efficacy classification | M5/M6 | Deterministic checks preferred; judge strategy validated before strong rubric claims |
| Strict isolation parity | Qualification evidence cannot claim v1 strongest attestation | M5/M6 | Smallest strict-confirmation path documented and validated |
| Kilo provider | Prototype CLI integration not productized | M5 | Thin Promptfoo provider with no generic wrapper architecture |
| Kilo Layer C | Natural skill activation not observed | future/M5+ | Native event required; otherwise remains `not_run` / limited |
| Limited execution/profile coverage | Generalization unknown | ongoing/M6 | Bounded sparse-evidence reporting; no exhaustive requirement |
| Raw result retention | Historical analysis may lack raw exports | M3/M6 | Durable artifact/hash/retention policy implemented |

Only explicitly recorded gaps are authorized. New large gaps require renewed
review.

## Evidence summary

### M1 results

**Layer A development routing (review-family, 3 reps):**

| metric | value |
| --- | --- |
| attempted | 54 |
| successful | 54 |
| failed | 0 |
| correct | 52 |
| incorrect | 2 |
| accuracy (over successful) | 0.963 |

v1 successful-decision accuracy was approximately `0.981`. Differences were
consistent with model/provider nondeterminism, not a systematic Promptfoo
semantic break.

**Frozen holdout (review-discrim-1):**

| revision | correct |
| --- | --- |
| v1 | 21/21 |
| Promptfoo | 21/21 |

No rep-level difference.

### Layer B representative execution

- `code-review` target: applied authorized fixes, did not merge, did not
  claim approval/readiness.
- `code-review` no-skill baseline: merged the branch and wrote approval/
  readiness language.

This demonstrates the framework can observe skill benefit AGK cares about.
N=1 per cell — not universal efficacy.

### Candidate/reference comparison

Distinct skill revisions with distinct hashes and controlled comparison
conditions. No material difference was detected on the selected case. This is
a valid result (`no material difference detected in this tested comparison`),
not `the revisions are universally equivalent`.

## M1 planning corrections (M2 supersession)

The M1 report's planning statements are explicitly superseded here without
rewriting the historical record:

### Correction 1 — canonical corpus ownership after migration

The M1 report depicted AGK as "portable skills only (+ canonical eval corpus)"
as a final state. That is **transitional**.

**During migration/parity window:**

```text
agent-guidance-kit
    skills
    existing evaluator
    canonical corpus temporarily remains

agent-guidance-kit-evals
    being established
```

**Final intended state after M4/M7:**

```text
agent-guidance-kit
    portable skills
    adoption docs
    lightweight integrity CI

agent-guidance-kit-evals
    canonical AGK eval corpus
    confusion sets
    holdout
    methodology
    Promptfoo configs/integrations
    provenance/evidence history
```

The eval repository becomes the canonical owner of the evaluation corpus. AGK
must not retain a hidden evaluator product after the split.

### Correction 2 — judge reliability and isolation are separate concerns

Semantic grading reliability and execution/isolation attestation are recorded
as separate concerns:

- **Semantic grading reliability gap** — the free-model `llm-rubric` judge
  produced repeated obvious grading inversions (e.g., refusal/deny language
  could be graded as if the worker declared merge readiness). A semantic judge
  problem is not fixed by container isolation.
- **Execution/isolation attestation gap** — the spike used independent
  disposable host workspaces. This is adequate for qualification-style
  experiments but does not replicate the strongest evaluator-v1 Docker/
  runtime attestation. Do not delete the existing strict-confirmation path
  until M5/M6 determines the smallest necessary replacement.

### Correction 3 — raw evidence retention is explicitly unresolved

The M1 report did not emphasize strongly enough that the spike's `.results/`
directory was git-ignored. Raw artifacts may not survive branch deletion. The
historical status and a future retention policy are recorded in
[`promptfoo-spike/README.md`](../evaluations/promptfoo-spike/README.md) and
[`promptfoo-spike/evidence-manifest.json`](../evaluations/promptfoo-spike/evidence-manifest.json).

## Rejected alternatives

### Continue growing evaluator v1 in AGK

Rejected as the long-term architecture. It combines two products in one
repository and contradicts AGK's original identity as a portable skill library.
Evaluator v1 remains temporarily as the control/reference, not the target.

### Extract evaluator v1 wholesale into a generic `agent-skill-evaluator`

Rejected. Promptfoo already occupies the generic engine role. Building another
generic provider, runner, assertion framework, reporter, UI, or model client
abstraction would duplicate Promptfoo without value.

### Merge the spike wholesale into AGK

Rejected. The spike is experimental evidence, not production architecture.
Importing its lockfile, generated projections, prototype providers, spike-only
tests, and hard-coded representative selection would pollute AGK's product
surface with experimental artifacts.

### Abandon Promptfoo

Rejected by current evidence. Reconsider only if future M3–M6 work shows that
preserving AGK semantics requires a large disguised parallel framework around
Promptfoo.

## Consequences

- M3 (`agent-guidance-kit-evals` foundation) is now **authorized**.
- The spike branch remains isolated under `experiments/promptfoo/` and is not
  merged, rebased wholesale, cherry-picked wholesale, or deleted.
- No Promptfoo runtime dependency or generated projection is added to AGK's
  product surface.
- The existing evaluator v1, skills, corpus, and holdout are unchanged.
- Future M3–M8 work proceeds with the gap batch explicitly recorded and bounded.

## References

- M1 evidence commit: `217d53f5db7ea01d4fd4fadbefdfe987f663cbb6`
- Frozen baseline: `91ed0155e83d70d0b80a7912d63a2a1c16660b0f`
- Architecture: `docs/evaluations/evidence-evaluator-architecture.md`
- Milestone tracker: `docs/evaluations/evidence-evaluator-milestones.md`
- Historical M1 report: `docs/evaluations/promptfoo-spike/M1-REPORT.md`
- Kilo next steps (design note): `docs/evaluations/promptfoo-spike/KILO-NEXT.md`
- Evidence manifest: `docs/evaluations/promptfoo-spike/evidence-manifest.json`
