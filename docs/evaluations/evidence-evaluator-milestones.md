# Promptfoo-backed evaluator milestone tracker

**Status:** M0–M4 complete; M5 authorized and not started. Canonical evaluation-corpus ownership now lives in `agent-guidance-kit-evals`; the AGK copies of the corpus are a frozen legacy evaluator-v1 compatibility/reference copy until M7.

**Parent design:** [Promptfoo-backed evaluation architecture for Agent Guidance Kit](evidence-evaluator-architecture.md)

**Source discussion:** [shared conversation](https://chatgpt.com/share/6a8aafd3-322c-83ea-87c5-c49812cd88f4)

**M2 ADR:** [ADR-0001: Promptfoo-backed evaluator — GO WITH MATERIAL GAPS](../adr/0001-promptfoo-backed-evaluator.md)

**M1 evidence:** [Historical evidence area](promptfoo-spike/M1-REPORT.md) (copied verbatim from `experiments/promptfoo/REPORT.md` at `217d53f5db7ea01d4fd4fadbefdfe987f663cbb6`)

This tracker follows the conversation's final architecture: Promptfoo is the
candidate commodity engine; a future `agent-guidance-kit-evals` repository owns
AGK corpus, methodology, thin integrations, Kilo support, provenance, and
historical evidence; Agent Guidance Kit returns to being a lightweight portable
skill library.

No split or deletion is authorized until the compatibility spike earns a
`GO`/approved `GO WITH MATERIAL GAPS` decision.

## Status vocabulary

- `not started` — scoped but no implementation evidence exists.
- `in progress` — work is active but exit evidence is incomplete.
- `blocked` — a named dependency prevents progress.
- `complete` — every exit criterion has recorded evidence.
- `deferred` — intentionally excluded from the current delivery window.
- `rejected` — evidence showed the approach should not proceed.

## Milestone overview

| ID | Milestone | Status | Depends on | Decision/outcome |
| --- | --- | --- | --- | --- |
| M0 | Correct architecture and freeze assumptions | `complete` | — | Promptfoo-first governing design established and maintainer-reviewed. |
| M1 | Complete Promptfoo compatibility spike | `complete` | M0 | Valid `REPORT.md`, v1/v2 comparison, tests, and review. Spike commit: `217d53f5db7ea01d4fd4fadbefdfe987f663cbb6`. Historical evidence preserved at `docs/evaluations/promptfoo-spike/`. |
| M2 | Promptfoo go/no-go decision | `complete` | M1 | `GO WITH MATERIAL GAPS`. See [ADR-0001](../adr/0001-promptfoo-backed-evaluator.md). |
| M3 | Create `agent-guidance-kit-evals` foundation | `complete` | M2 = GO, or approved GO WITH MATERIAL GAPS after gap recheck | Foundation commit `56600a8`; hardened and merged at `5fa650b3`; 26 skills discovered; 33 tests; AGK not mutated. |
| M4 | Migrate canonical corpus and history | `complete` | M3 | Migrated at eval-repo merge `cb1c1651` from AGK source `8ac3f7b`; 26 packs / 145 canonical files; holdout hash parity verified; 20 historical-v1 artifacts; AGK not mutated. |
| M5 | Establish thin Promptfoo/Kilo integration | `authorized / not started` | M3–M4 | Promptfoo owns mechanics; AGK layer owns demonstrated gaps only. |
| M6 | Prove parity, evidence policy, and historical aggregation | `not started` | M4–M5 | Bounded evidence claims and classified v1/v2 differences. |
| M7 | Clean Agent Guidance Kit | `not started` | M6 | Lean copy/adapt library with lightweight static CI. |
| M8 | Prove independent operation and harden | `not started` | M7 | Clean AGK externally evaluated; both repos independently healthy. |

## M0 — Correct architecture and freeze assumptions

**Objective:** Establish the actual decision from the complete conversation and
avoid implementing the first draft's incorrect custom-engine direction.

### Work items

- [x] Create a dedicated architecture worktree from `main`.
- [x] Traverse and inspect all 23 user prompt sections and responses in the
      shared conversation.
- [x] Record the evolution from product split, to generic evaluator proposal,
      to Promptfoo-backed thin eval repository.
- [x] Add Promptfoo, Kilo, external-target, execution-profile, holdout, and
      evidence-policy requirements to the parent design.
- [x] Maintainer reviews and approves/corrects the architecture.

### Exit criteria

- Parent design accurately reflects the complete conversation.
- Maintainer has reviewed and approved/corrected the architecture.
- Promptfoo's role is explicitly conditional on spike evidence.
- No custom generic engine work is authorized by default.
- Open decisions are deferred to M2 where the spike can inform them.

## M1 — Complete the Promptfoo compatibility spike

**Objective:** Determine whether Promptfoo can replace most home-grown mechanics
while preserving AGK's experimental semantics.

**Status:** `complete`

**Active location:** `spike/promptfoo-compat`, isolated under
`experiments/promptfoo` in the other worktree.

**Evidence commit:** `217d53f5db7ea01d4fd4fadbefdfe987f663cbb6`

**Historical evidence preserved:** `docs/evaluations/promptfoo-spike/M1-REPORT.md`,
`docs/evaluations/promptfoo-spike/KILO-NEXT.md`,
`docs/evaluations/promptfoo-spike/evidence-manifest.json`.

The presence of files is not completion evidence. Results, comparisons, gates,
and fresh-context review must exist.

### M1.1 Freeze the comparison point

- [x] Record spike branch, starting/ending HEAD, `main` SHA, and worktree status.
- [x] Record exact Promptfoo, Python, Node, Kilo, harness, provider/backend,
      model, and environment identifiers/versions where available. Explicitly
      record `unknown`, `unreported`, or unresolved aliases rather than guessing.
- [x] Keep unrelated changes and skill bodies out of the spike diff.
- [x] Keep evaluator v1 fully intact and usable as the reference control.

### M1.2 Layer A development routing

- [x] Generate Promptfoo tests from canonical
      `evaluations/confusion-sets/review-family.json`.
- [x] Exercise all 17 development cases, including multi-turn cases.
- [x] Preserve expected skill, actual skill, explicit null, and failure as
      distinct states.
- [x] Enforce decision-level `attempted = successful + failed`.
- [x] Treat Promptfoo as the evaluation engine, not a coding-agent harness;
      record Layer A with `harness: none` and an execution context such as
      `catalog_router` where appropriate.
- [x] Preserve exact raw provider/harness settings; leave unverified normalized
      semantics unknown.
- [x] Identify cached responses and confirm they do not count as independent
      repetitions.
- [x] Count one experimental repetition as one decision even when it contains
      multiple provider/infrastructure attempts. Preserve invocation-attempt,
      retry-count, retry-failure, and retry-reason history where applicable;
      exhausted retries produce one failed decision.
- [x] Produce a confusion matrix, decision accuracy over successful decisions,
      per-skill counts, and transition correctness. Use attempted decisions for
      coverage/failure accounting, and never turn failed or exhausted-retry
      samples into incorrect or null decisions.
- [x] Choose repetitions adaptively. Three may be useful where practical, but
      there is no universal count; label limitations from wall-clock/runtime,
      rate limits, provider/free-tier/model availability, and cost.

### M1.3 Layer B representative execution

- [x] Generate cases from canonical eval JSON for `code-review`,
      `security-review`, and `architecture-review`.
- [x] Run approximately 2–3 suitable execution cases per skill where corpus
      support exists.
- [x] Cover committed/generated fixture behavior where practical, read-only and
      mutation cases, deterministic checks, and semantic rubric checks.
- [x] Run at least one target/no-skill comparison per representative skill.
- [x] Use independent starting workspaces per case × condition × repetition.
- [x] Hold harness mode and permissions constant across target/baseline unless
      mode sensitivity is the declared experiment; record whether each mode was
      capable of the requested operation.
- [x] Apply `skill-contract` only to target; apply `shared-outcome` and
      `universal-safety` fairly across conditions.
- [x] Add one placebo comparison if it remains a thin Promptfoo configuration,
      not a custom framework project.

### M1.4 Revision comparison

- [x] Demonstrate one `code-review` candidate/reference comparison using actual
      Git revisions.
- [x] Hold task, fixture, harness/mode, model/reasoning profile, provider,
      tools, permissions, system/agent profile where relevant, and assertions
      constant or materially equivalent.
- [x] Record candidate/reference SHAs, skill hashes, fixture hash, case identity,
      and Promptfoo version.
- [x] Verify candidate/reference starting target content is identifiable and
      does not silently depend on unknown dirty or untracked local state.
- [x] Do not attribute a difference to the skill revision when materially
      behavior-changing execution-profile dimensions differ, including a known
      resolved-backend difference unless shown immaterial; report such runs as
      portability, coverage, or an intentional interaction experiment.
- [x] Avoid rebuilding a generic regression runner.

### M1.5 Frozen holdout

- [x] Do not edit or tune against `review-discrim-1.json`.
- [x] Stabilize development implementation before invoking holdout.
- [x] Run one unchanged post-stabilization holdout evaluation.
- [x] If infrastructure invalidates a run, record why and do not use observed
      model behavior to tune implementation/skills.
- [x] If valid holdout behavior informs a skill, routing, evaluator, or expected
      outcome change, mark that holdout version `consumed`,
      `retired_for_holdout`, or equivalent before the next generalization claim.
- [x] Report development and holdout separately.

### M1.6 Kilo evidence note/integration

- [x] Use documented Kilo JSON/CLI behavior only.
- [x] Capture output, errors, tokens, latency, model, repeat, and session identity
      when available.
- [x] Classify activation evidence as native, heuristic, forced, behavioral, or
      none/unknown.
- [x] Keep forced activation as Layer B evidence.
- [x] Keep Layer C `not_run`/limited unless actual Kilo evidence meets the
      definition.
- [x] Identify which Kilo functionality should be proposed upstream to
      Promptfoo.

### M1.7 v1/v2 comparison and report

- [x] Compare overlapping routing prompts, labels, outputs, failures,
      repetitions, metrics, fixtures, condition identity, assertions, and
      provenance.
- [x] Classify each material difference as expected engine difference,
      Promptfoo limitation, v1 limitation, prototype bug, model nondeterminism,
      provider/harness difference, or unknown.
- [x] Produce `experiments/promptfoo/REPORT.md` with one of: `YES`,
      `YES, WITH MATERIAL GAPS`, `NO`, `INCONCLUSIVE`.
- [x] Include file-by-file future disposition and measured code-deletion
      estimate.
- [x] State exactly what remains custom and why.
- [x] Run the repository gate and Promptfoo spike tests/config validation.

### M1.8 Required fresh-context review

- [x] Launch the repository-required fresh read-only adversarial reviewer before
      any push.
- [x] Review for unnecessary wrappers, duplicated provider/assertion/reporting
      logic, holdout leakage, baseline unfairness, failure/null conflation,
      workspace contamination, unsupported Layer C claims, provenance gaps, and
      benchmark tuning.
- [x] Apply findings only in a separately authorized change pass.
- [x] Address material high-confidence defects. If those fixes materially change
      the implementation or evidence, rerun the fresh-context review; record
      accepted residual limitations explicitly.

### Exit criteria

- All required experiment classes have actual evidence or explicit justified
  limitations.
- Existing evaluator and skill corpus remain unchanged as experimental inputs.
- The report is sufficient to decide M2 without relying on feature-list claims.
- The adversarial review converges on no unresolved material findings; no magic
  verdict word is required. Repository review-before-push policy still applies.

## M2 — Promptfoo go/no-go decision

**Objective:** Make an explicit architecture decision from spike evidence.

**Status:** `complete`

**Decision:** `GO WITH MATERIAL GAPS`

**ADR:** [ADR-0001: Promptfoo-backed evaluator — GO WITH MATERIAL GAPS](../adr/0001-promptfoo-backed-evaluator.md)

**M3:** `authorized` at decision time (historical); M3 has since been implemented and completed. See the M3/M4 sections and the decision log below.

### Decision review

- [x] Verify all M1 results are protocol-usable at their claimed level.
- [x] Quantify generic machinery Promptfoo replaces using actual lines/files.
- [x] Quantify custom code retained by category: corpus conversion, metrics,
      policy, provenance, workspace, Git target, Kilo, strict isolation.
- [x] Determine whether custom code is thin or a disguised parallel framework.
- [x] Verify remaining custom code is demonstrably limited to AGK-specific
      semantics, corpus conversion, provenance, workspace controls, and genuine
      provider gaps.
- [x] Ask whether observed v1/v2 differences are attributable to
      execution-profile changes rather than evaluator behavior.
- [x] Verify Promptfoo caching/retry behavior preserves AGK evidence semantics.
- [x] Verify the design avoids universal-score assumptions and keeps materially
      different profiles visible.
- [x] Verify unknown or unverified runtime semantics remain unknown and exact
      raw provider/harness settings are preserved.
- [x] Review unresolved v1/v2 differences and unknowns.
- [x] Review Promptfoo dependency/maturity risks and version-pinning strategy.
- [x] Decide repository name and migration provenance approach.

### Decision branches

#### `GO`

- Promptfoo absorbs the clear majority of commodity mechanics.
- Remaining custom code expresses AGK semantics or a real provider gap.
- M3 is authorized.

#### `GO WITH MATERIAL GAPS` (selected)

- Record each gap, owner, size, risk, and acceptance criterion.
- Approve the complete gap batch, not open-ended wrapper development.
- Do not begin M3 from this outcome until the approved gaps are addressed and
  the go/no-go gate is rechecked.

#### `NO`

- Mark M3–M8 for the Promptfoo route `rejected`.
- Revisit standalone evaluator or another engine using the spike evidence.

#### `INCONCLUSIVE`

- Define the smallest additional spike evidence needed.
- Do not split repositories or consume holdout as development feedback.

### Exit criteria

- ADR records decision, evidence, rejected alternatives, and explicit gaps.
- No migration begins from an implicit “the prototype runs” conclusion.

### M2 evidence summary

See `docs/evaluations/promptfoo-spike/` for full details and
`docs/adr/0001-promptfoo-backed-evaluator.md` for the complete ADR.

## M3 — Create `agent-guidance-kit-evals` foundation

**Objective:** Establish an independent Promptfoo-backed project that targets an
external, still-intact AGK checkout.

**Status:** `complete`

**New repository:** `agent-guidance-kit-evals` (under the same GitHub organization as AGK)

**Foundation commit:** `56600a8` (initial `main` commit)

**Hardened M3 commit:** `5fa650b3` (final merged `main` in agent-guidance-kit-evals after hardening: committed reproducible npm lockfile, `npm ci --ignore-scripts`, Promptfoo 0.122.0 assertion, config validation, deterministic echo-provider smoke, corrected Git revision resolution, expanded revision tests, durable/local-only evidence retention clarification, lint cleanup)

**External-target smoke evidence:**

- Local-path mode: 26 AGK skills discovered in external checkout at
  `f26bde74f8e4186ade94c6438bf56d03f2541c07`; AGK not mutated.
- Revision-addressable mode: 26 skills discovered from clean Git clone at
  `f26bde74f8e4186ade94c6438bf56d03f2541c07`; resolved revision verified;
  target cleaned up after test.

**Deterministic tests:** 33 unit tests pass without network, model access, or
AGK checkout.

### Deliverables

- New repository with README, AGENTS, license/provenance note, pinned Promptfoo,
  and deterministic CI.
- Explicit target profile separating evaluator, target, suite, output, and
  workspace roots.
- Local-path target and revision-addressable target support needed by current
  cases.
- Thin code migrated from the spike only after classification/review.
- Local fake/example target so unit tests do not require AGK checkout.

### Exit criteria

- Eval repository discovers external AGK skills without target-local eval files.
- AGK is still unchanged and its v1 evaluator still passes.
- No generic Promptfoo wrapper CLI/framework has appeared.

## M4 — Migrate canonical corpus and history

**Objective:** Move evaluation ownership without rewriting corpus semantics or
historical truth.

**Status:** `complete`

**Migration record:** `MIGRATION.md` and `migration/m4-source-manifest.json` in
`agent-guidance-kit-evals`.

**Evidence:**

- Source AGK extraction revision: `8ac3f7bf01fc06ebffc826da3e090c1085c91485`
  (frozen; all migrated content extracted from this single snapshot).
- Eval-repo M4 merge SHA: `cb1c1651b36218ba449aa979510b442ecac38cc9`
  (eval-repo PR #2, hosted CI green).
- Canonical corpus: 26 per-skill eval packs (140 files) + 4 confusion-set
  families + 1 protected holdout file = 145 canonical files.
- Holdout hash parity:
  `sha256:e2ad6dac06d64f8efad17df96d6c6f3af13c7f3a88aac25b19fe87587936dd35`
  identical on both sides; holdout not run and not used for tuning.
- Historical v1 evidence: 20 artifacts under `historical-v1/` (results,
  summaries/reports, inventory, environment record, methodology reference
  snapshots); statuses such as `invalid`, `limited`, `not_run` preserved
  verbatim; no historical truth rewritten.
- Integrity verification: deterministic manifest + `scripts/verify_migration.py`;
  full source parity run against a fresh clone of the frozen SHA confirmed
  165/165 files byte-equal (0 mismatches, 0 missing, 0 unexpected); fresh-context
  adversarial review returned PASS with no findings.
- Known provenance gaps recorded in `MIGRATION.md`: raw `.eval-evidence/`
  artifacts are local-only and were never committed upstream; standalone
  committed routing reports do not exist for evaluator v1 outside SUMMARY.md;
  per-artifact historical run revisions remain unreported/unverified where the
  artifact itself does not record them.

### Deliverables

- Per-skill eval packs under eval-repo corpus. — done (`corpus/skills/<skill>/evals/`)
- Development confusion sets and physically separate holdout. — done (`corpus/confusion-sets/`, `corpus/holdout/`)
- Target profile mapping corpus skill identities to external target skills. — done (`profiles/agk-target-skills.json`)
- Historical schema-v3 results, summaries, validation matrix, routing reports,
  and frontmatter inventory under `historical-v1`. — done (standalone routing-report files do not exist in v1; recorded as a provenance gap)
- `MIGRATION.md` with source repository, commit, extraction date, path mapping,
  and known provenance gaps. — done
- Hash comparison showing fixtures/suites remained stable where intended. — done (manifest + verifier)

### Exit criteria

- Canonical corpus has one owner. — met: `agent-guidance-kit-evals` is canonical; the AGK copies are a frozen legacy evaluator-v1 compatibility/reference copy until M7 and are not independently editable canonical sources.
- Generated Promptfoo projections are reproducible and not hand-maintained. — met for M4 scope: no hand-maintained projections exist; production projection generators are M5 deliverables (milestone boundary clarified in `MIGRATION.md`).
- Historical invalid/limited/not-run labels remain unchanged. — verified byte-for-byte.
- Holdout content and identity match the frozen source. — verified by hash parity.

## M5 — Establish thin Promptfoo/Kilo integration

**Objective:** Productize only the custom surface demonstrated necessary by M1/M2.

**Status:** `authorized / not started`

### Deliverables

- Corpus generators for routing and execution.
- AGK routing metrics and failure accounting.
- Baseline-fairness/protocol-claim checks.
- Provenance envelope and narrow validator.
- Git/local target materialization with clean, dirty, and non-Git starting-state
  identity sufficient to distinguish actual evaluated content.
- Independent workspace management where providers need it.
- Kilo provider or upstream integration, with evidence-source classification.
- Optional strict Docker confirmation mode if still required.

### Guardrails

- [ ] No GenericProvider abstraction around Promptfoo providers.
- [ ] No generic runner/concurrency/retry engine.
- [ ] No generic assertion engine or report renderer.
- [ ] No duplicate Codex/Claude/OpenCode providers.
- [ ] No unsupported promotion of skill reads to native activation.
- [ ] No global ordered reasoning-effort assumption.
- [ ] No execution-profile normalization that destroys exact raw
      provider/harness values or invents semantics for unknown settings.
- [ ] No custom cache/retry engine around Promptfoo.
- [ ] No causal revision comparison across unmatched execution profiles.

### Exit criteria

- Custom code maps directly to a documented AGK semantic/provider gap.
- Promptfoo upgrades can be tested without rewriting the corpus.
- Kilo/free-model/provider freedom remains practical.

## M6 — Prove parity, policy, and historical aggregation

**Objective:** Show that the new system preserves meaning and supports bounded
confidence claims over accumulated sparse evidence.

### Deliverables

- Representative deterministic and model-backed parity matrix against v1.
- Evidence aggregation preserving attempted/successful/failed/invalid/not-run
  denominators.
- Execution-profile identity covering behaviorally material provider, model,
  raw reasoning/preset, agent mode, tool/permission, system/orchestration, and
  environment configuration; coding-agent harness identity where applicable.
- Sample/run metadata covering run ID, timestamp, repeat index, seed/random
  controls, invocation/retry history, and cache identity without making each
  repetition a separate execution profile.
- Requested/resolved gateway backend identity where reported, explicit
  unknown/unreported values, and optional context-management/compaction identity
  where behaviorally material.
- Reproducible starting-target identity for clean Git, dirty Git, and non-Git
  local targets, with content-aware untracked identity and without hashing
  irrelevant transient output.
- Adjacent run-economics and availability metadata without treating them as
  automatically behavior-changing profile identity.
- Scope labels: smoke, targeted, qualification, holdout, confirmation.
- One documented default AGK qualification policy, with lightweight optional
  project/user overrides only where demonstrated needs justify them.
- Factual per-profile result summaries using observed, supported, qualified, and
  strongly supported as reporting language.
- Explicit evidence-gap reporting and per-skill historical coverage.
- Revision comparison summaries based on controlled paired evidence.

### Exit criteria

- Same inputs reproduce projections and aggregates.
- Durable raw artifacts remain immutable while versioned validation, analysis,
  and confidence interpretations may explicitly supersede earlier results.
- Derived indexes rebuild against the selected/current analyzer version without
  silently rewriting historical raw evidence or prior interpretations.
- Policy failure reports missing evidence, not skill failure.
- No percentage appears without denominator, scope, execution profile, and a
  visible breakdown for any justified cross-profile aggregation.
- The implementation does not require a policy DSL, generalized claim-language
  generator, or elaborate configuration taxonomy.
- No historical v1 result is silently reinterpreted as v2 evidence.

## M7 — Clean Agent Guidance Kit

**Objective:** Restore AGK's original portable copy/adapt product identity.

### Preconditions

- M3–M6 complete.
- Eval repository successfully evaluates intact external AGK.
- Complete moved/retained/deleted path inventory approved.
- Fresh review completed before any update push.

### Deliverables

- Remove evaluator runners, schemas, validators, Docker infrastructure, results,
  confusion sets, holdout, and per-skill eval packs from AGK.
- Rewrite README around browse → review → select → copy/adapt.
- Split AGENTS guidance so evaluation policy lives in the eval repository.
- Remove framework-bound `skill-evaluation` from AGK; defer or separately author
  a small framework-neutral replacement.
- Replace heavy evaluator CI with frontmatter/catalog/link integrity checks.
- Remove no-longer-needed Python/CodeQL dependencies only when final files prove
  they are unnecessary.
- Audit every cross-repository and relative link.

### Exit criteria

- AGK contains no hidden evaluator implementation or dangling paths.
- A user can adopt a skill without knowing the eval repository exists.
- AGK deterministic gate passes independently.

## M8 — Prove independent operation and harden

**Objective:** Demonstrate the split is architectural, not cosmetic.

### Cross-project proofs

- [ ] Eval repository evaluates cleaned AGK externally.
- [ ] Eval repository does not modify the canonical target; mutations occur only
      in disposable workspaces.
- [ ] Removing eval checkout does not break AGK.
- [ ] Removing AGK checkout still leaves eval-repo unit tests usable with local
      fixtures/example target.
- [ ] Both repositories pass independent native gates.
- [ ] Model-backed runs are manual/scheduled, not required for ordinary AGK PRs.

### Hardening and upstreaming

- [ ] Security review raw evidence retention, subprocess/provider inputs,
      workspaces, credentials, and report sanitization.
- [ ] Architecture review generic-versus-target-specific boundaries.
- [ ] Propose Kilo provider and broadly useful skill-call/confusion/provenance
      improvements upstream to Promptfoo where appropriate.
- [ ] Final fresh-context adversarial review leaves no unresolved material
      findings; accepted residual limitations are recorded.

### Exit criteria

- Each README describes exactly one coherent product.
- Promptfoo owns commodity mechanics in practice, not just diagrams.
- AGK evidence claims remain bounded, reproducible, and traceable.

## Cross-cutting acceptance checklist

### Experimental integrity

- [ ] Failed provider call never becomes explicit null.
- [ ] Routing, post-activation efficacy, and native harness activation remain
      separate questions.
- [ ] Baselines receive no target guidance and no target-only grading.
- [ ] Conditions start independently from the same natural task/fixture.
- [ ] A pristine holdout is not used for tuning while retaining holdout status.
      If valid holdout behavior informs development, that version is explicitly
      consumed/reclassified before another independent-generalization claim.
- [ ] Holdout lifecycle status distinguishes pristine, consumed/retired, and
      infrastructure-invalid evidence without elaborate secret-test machinery.
- [ ] Placebo remains available for stronger specific-effect claims.
- [ ] Protocol validity remains distinct from task score.
- [ ] Harness mode and permissions permit the requested operation, or their
      capability difference is an explicit mode-sensitivity variable.
- [ ] Cached responses are not independent repetitions. One experimental sample
      may contain multiple retry attempts; retry failures remain invocation
      history, and exhausted retries produce one failed experimental sample.

### Provenance

- [ ] Target, eval layer, suite, case, fixture, projection, Promptfoo, provider,
      model, raw reasoning/preset, mode, and analyzer identities are recorded;
      coding-agent harness identity is recorded where applicable.
- [ ] Layer A may validly record `harness: none` and `catalog_router` execution
      context without labeling Promptfoo as the coding-agent harness.
- [ ] Requested and resolved model IDs are distinguished where possible.
- [ ] Gateway identity and resolved inference provider/backend are distinguished
      where reported; hidden routing is not inferred.
- [ ] Non-reasoning, reasoning mode, effort, and compound presets are not
      collapsed incorrectly.
- [ ] Raw provider/harness values remain authoritative; normalized values are
      secondary and unknown semantics remain unknown.
- [ ] Unknown/unreported harness, provider/backend, model, snapshot, and preset
      identifiers are recorded explicitly rather than guessed and are not
      automatically protocol failures.
- [ ] Starting target identity distinguishes clean Git, dirty/untracked Git, and
      non-Git local content relevant to the execution; untracked identity is
      content-aware rather than filename-only.
- [ ] Behavioral execution identity is distinct from run economics and
      availability metadata.
- [ ] Repeat index, timestamp, seed/random controls, invocation/retry history,
      and cache identity are sample/run metadata by default; behaviorally
      material environment configuration remains part of execution identity.
- [ ] Raw artifacts are content-addressed/sanitized or explicitly local-only.
- [ ] Raw evidence remains immutable; versioned validation/analysis may
      explicitly supersede an earlier interpretation without silent rewriting.

### Claim discipline

- [ ] Every metric has numerator, denominator, and scope.
- [ ] Every claim names tested configuration and unknown coverage.
- [ ] Revision improvement/regression claims use controlled paired profiles;
      cross-profile evidence is labeled portability/generalization evidence.
- [ ] `n=1` is observed/pilot evidence unless policy explicitly supports more.
- [ ] No `proven` or universal reliability language.
- [ ] Missing combinations remain unknown, not failures, and no universal AGK
      score hides materially different execution profiles.
- [ ] Policy gaps do not erase observations.

### Product boundaries

- [ ] AGK does not depend on Promptfoo/eval repo.
- [ ] Eval repo does not require target-local eval files.
- [ ] Custom code is AGK-specific or a documented Kilo gap.
- [ ] Promptfoo APIs are not reimplemented behind wrappers.

## Decision log

| Date | Decision | Status | Evidence/notes |
| --- | --- | --- | --- |
| 2026-08-23 | Separate the portable skill library from evaluation ownership. | accepted | Full shared conversation. |
| 2026-08-23 | Do not build a new generic evaluator by default; evaluate Promptfoo as engine. | accepted, gated | Landscape/code-level comparison and compatibility-spike specification. |
| 2026-08-23 | Preserve AGK corpus/methodology/provenance/Kilo integration in a thin eval repository. | accepted | Parent architecture. |
| 2026-08-23 | Keep evaluator v1 intact until Promptfoo equivalence is demonstrated. | active constraint | M1 spike requirements. |
| 2026-08-23 | Treat evidence as sparse facts interpreted by policy, not certification. | accepted | Later evidence/confidence discussion. |
| 2026-08-23 | **M2 decision: GO WITH MATERIAL GAPS.** Proceed toward Promptfoo-backed eval repository with explicitly recorded gaps. | accepted | M1 spike evidence at `217d53f5db7ea01d4fd4fadbefdfe987f663cbb6`; ADR-0001. M3 authorized. |
| 2026-08-23 | **M3 complete.** `agent-guidance-kit-evals` repository founded at `56600a8`; hardened and merged at `5fa650b3`. | accepted | 26 AGK skills discovered in external checkout; 33 unit tests pass; committed npm lockfile; reproducible `npm ci`; Promptfoo 0.122.0 asserted; config validation; deterministic echo-provider smoke; corrected Git revision resolution; durable/local-only evidence distinction; AGK not mutated. |
| 2026-08-23 | **M4 complete — canonical corpus ownership migrated.** `agent-guidance-kit-evals` is now canonical for evaluation corpus changes; the remaining AGK corpus is a frozen legacy evaluator-v1 compatibility/reference copy until M7. | accepted | Eval-repo merge `cb1c1651` from AGK source `8ac3f7b`; 26 packs / 145 canonical files migrated as exact copies; holdout hash parity `sha256:e2ad6dac…dd35`; 20 historical-v1 artifacts with labels preserved verbatim; 165/165 source-parity verified; fresh-context review PASS. |

## Immediate next actions

1. M0–M4 complete.
2. Historical M1 evidence preserved at `docs/evaluations/promptfoo-spike/`.
3. Future corpus edits originate in `agent-guidance-kit-evals` (`corpus/`); do not edit the AGK corpus copies in parallel.
4. M5 (thin Promptfoo/Kilo integration) is authorized and not started; wait for explicit maintainer go-ahead before implementing it.
