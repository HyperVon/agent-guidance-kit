# M2 Review — Promptfoo go/no-go decision

**Status:** M2 complete — `GO WITH MATERIAL GAPS`

**Date:** 2026-08-23

**M2 branch:** `m2/promptfoo-go-decision` from `origin/main` at
`bfbd03d3f655c97a063dd945f2ee254f0b57e01d`

**M1 evidence commit:** `217d53f5db7ea01d4fd4fadbefdfe987f663cbb6`

**Frozen baseline:** `91ed0155e83d70d0b80a7912d63a2a1c16660b0f`

**ADR:** `../adr/0001-promptfoo-backed-evaluator.md`

## Phase 1 — Input verification record

| item | value |
| --- | --- |
| `origin/main` SHA | `bfbd03d3f655c97a063dd945f2ee254f0b57e01d` |
| M1 spike evidence commit | `217d53f5db7ea01d4fd4fadbefdfe987f663cbb6` |
| frozen baseline | `91ed0155e83d70d0b80a7912d63a2a1c16660b0f` |
| spike branch | `spike/promptfoo-compat` (not merged, exists at `217d53f...`) |
| Promptfoo version | `0.122.0` |
| Kilo CLI | `7.4.23` |
| Python | `3.14.6` |
| Node | `26.7.0` |
| tested model/provider | `kilo/tencent/hy3:free` |
| spike date | 2026-08-23 |
| `.results/` still present | Yes, in the spike worktree at `experiments/promptfoo/.results/` |

Worktree status at M2 branch creation: clean (tracking `origin/main`),
untracked `docs/evaluations/promptfoo-spike/` and `experiments/` directories.

## Phase 3 — Raw result retention status

The spike's `.results/` directory was git-ignored and therefore is not present at
commit `217d53f...`. The original files still survived in the spike worktree.
They were inspected for:

- secrets / credentials: none found (only Kilo session IDs and host paths)
- absolute local paths: present (`/tmp/kilo/agk-pf-workspaces/...`) in execution
  and regression results; stripped in sanitization
- session identifiers: present (Kilo `ses_fd...` session IDs) in result metadata;
  stripped in sanitization
- PII: none found
- machine-specific information: host workspace paths only
- unnecessarily huge model outputs: all results retained for hash-linking;
  outputs are bounded to the tested case set

Sanitized durable representations of each artifact are committed at
`docs/evaluations/promptfoo-spike/` with SHA-256 hashes linking them to the
originals. See `evidence-manifest.json`.

Original raw artifacts remain **local-only** at:

```
experiments/promptfoo/.results/
```

This is classified as a known M1 provenance/retention gap: the original raw
artifacts are not version-controlled and could be lost if the spike worktree is
deleted. The sanitized copies in this directory provide durable but
non-authoritative representations.

## Phase 4 — M2 review findings

### Confirmed successful findings

**Promptfoo successfully demonstrated commodity-engine value:**

- Model invocation orchestration (Python custom providers wrapping `kilo run`)
- Experiment organization (separate configs per experiment)
- Assertions (protocol assertions, baseline-fairness scope)
- Result export (`-o results.json`)
- Caching control (`--no-cache`)
- Repetitions/row execution (explicit `rep` var)
- Layer A execution (catalog routing: 54/54 attempted, 52 correct, 2 incorrect)
- Layer B execution (target/baseline comparison)
- Candidate/reference comparison structure (regression config)

**AGK semantics remained separable:**

All custom code remained focused on AGK-specific concerns:
corpus projection, routing accounting, expected/null/failure semantics,
confusion metrics, assertion-scope/baseline fairness, Layer A/B/C claim gating,
workspace materialization, skill revision materialization, hashing/provenance,
Kilo-specific integration, strict-confirmation behavior.

**Layer A evidence was strong:**

| metric | v1 | Promptfoo |
| --- | --- | --- |
| Attempted | 54 | 54 |
| Successful | 54 | 54 |
| Failed | 0 | 0 |
| Correct | ~53 | 52 |
| Incorrect | ~1 | 2 |
| Accuracy | ~0.981 | 0.963 |

Frozen holdout: v1 21/21, Promptfoo 21/21 — no rep-level difference.

The 2 incorrect decisions were consistent with known model/provider
nondeterminism rather than a systematic Promptfoo semantic break.

**Layer B demonstrated real feasibility:**

- `code-review` target: applied authorized fixes, did not merge, did not claim
  approval/readiness
- `code-review` no-skill baseline: merged the branch, wrote approval/readiness
  language

This is good evidence the framework can observe the kind of skill benefit AGK
cares about. N=1 per cell — not universal efficacy.

**Candidate/reference comparison worked:**

Distinct skill revisions with distinct hashes and controlled comparison
conditions. No material difference detected on the selected case. This is a
valid result: `no material difference detected in this tested comparison`, not
`the revisions are universally equivalent`.

## Phase 5 — Material gaps (accepted)

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

## Phase 6 — M1 planning corrections (M2 supersession)

These corrections are recorded here without rewriting the historical M1
report. See the ADR for the full treatment.

### Correction 1 — Canonical corpus ownership after migration

The M1 report's "portable skills only (+ canonical eval corpus)" disposition is
**transitional**. The final architecture moves the canonical corpus to
`agent-guidance-kit-evals`. AGK must not retain a hidden evaluator product after
the split.

### Correction 2 — Judge reliability and isolation are separate

Semantic grading reliability (free-model `llm-rubric` judge instability) and
execution/isolation attestation (host workspaces vs. Docker attestation) are
separate concerns with separate solutions. Docker isolation does not fix judge
instability.

### Correction 3 — Raw evidence retention is explicitly unresolved

The M1 report did not emphasize that `.results/` was git-ignored. This is now
explicitly recorded as a limitation with a future retention policy requirement.

## Phase 14 — Fresh-context review outcome

A fresh-context review of the M2 changes confirms:

- [x] No prototype architecture was merged from the spike into AGK
- [x] Historical M1 report was not rewritten (copied verbatim with provenance header)
- [x] No overstatement of spike strength (N=1, nondeterminism, limited coverage)
- [x] No corpus-ownership contradiction (final state recorded as eval repo's)
- [x] Judge/isolation conflation avoided (Gap A and Gap B are separate)
- [x] Raw evidence caveat recorded (local-only artifacts, sanitized copies committed)
- [x] No vague unlimited GO WITH MATERIAL GAPS (bounded gap batch with owners)
- [x] No M3 implementation in M2 (authorized only)
- [x] No universal reliability language (evidence is sparse and bounded)
- [x] No unbounded new custom framework work (thin code only, as per constraints)
