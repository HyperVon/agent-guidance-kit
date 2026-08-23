# Promptfoo-backed evaluator milestone tracker

**Status:** Design-ready; M0 is complete and the M1 compatibility spike is
active in another worktree

**Parent design:** [Promptfoo-backed evaluation architecture for Agent Guidance Kit](evidence-evaluator-architecture.md)

**Source discussion:** [shared conversation](https://chatgpt.com/share/6a8aafd3-322c-83ea-87c5-c49812cd88f4)

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
| M1 | Complete Promptfoo compatibility spike | `in progress` | M0 | Valid `REPORT.md`, v1/v2 comparison, tests, and review. |
| M2 | Promptfoo go/no-go decision | `not started` | M1 | `GO`, approved `GO WITH MATERIAL GAPS`, `NO`, or `INCONCLUSIVE`. |
| M3 | Create `agent-guidance-kit-evals` foundation | `not started` | M2 = GO, or approved GO WITH MATERIAL GAPS after gap recheck | Independent eval repository targeting external AGK. |
| M4 | Migrate canonical corpus and history | `not started` | M3 | External suites/results with preserved provenance. |
| M5 | Establish thin Promptfoo/Kilo integration | `not started` | M3–M4 | Promptfoo owns mechanics; AGK layer owns demonstrated gaps only. |
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

**Active location:** `spike/promptfoo-compat`, isolated under
`experiments/promptfoo` in the other worktree.

The presence of files is not completion evidence. Results, comparisons, gates,
and fresh-context review must exist.

### M1.1 Freeze the comparison point

- [ ] Record spike branch, starting/ending HEAD, `main` SHA, and worktree status.
- [ ] Record exact Promptfoo, Python, Node, Kilo, harness, provider/backend,
      model, and environment identifiers/versions where available. Explicitly
      record `unknown`, `unreported`, or unresolved aliases rather than guessing.
- [ ] Keep unrelated changes and skill bodies out of the spike diff.
- [ ] Keep evaluator v1 fully intact and usable as the reference control.

### M1.2 Layer A development routing

- [ ] Generate Promptfoo tests from canonical
      `evaluations/confusion-sets/review-family.json`.
- [ ] Exercise all 17 development cases, including multi-turn cases.
- [ ] Preserve expected skill, actual skill, explicit null, and failure as
      distinct states.
- [ ] Enforce decision-level `attempted = successful + failed`.
- [ ] Treat Promptfoo as the evaluation engine, not a coding-agent harness;
      record Layer A with `harness: none` and an execution context such as
      `catalog_router` where appropriate.
- [ ] Preserve exact raw provider/harness settings; leave unverified normalized
      semantics unknown.
- [ ] Identify cached responses and confirm they do not count as independent
      repetitions.
- [ ] Count one experimental repetition as one decision even when it contains
      multiple provider/infrastructure attempts. Preserve invocation-attempt,
      retry-count, retry-failure, and retry-reason history where applicable;
      exhausted retries produce one failed decision.
- [ ] Produce a confusion matrix, decision accuracy over successful decisions,
      per-skill counts, and transition correctness. Use attempted decisions for
      coverage/failure accounting, and never turn failed or exhausted-retry
      samples into incorrect or null decisions.
- [ ] Choose repetitions adaptively. Three may be useful where practical, but
      there is no universal count; label limitations from wall-clock/runtime,
      rate limits, provider/free-tier/model availability, and cost.

### M1.3 Layer B representative execution

- [ ] Generate cases from canonical eval JSON for `code-review`,
      `security-review`, and `architecture-review`.
- [ ] Run approximately 2–3 suitable execution cases per skill where corpus
      support exists.
- [ ] Cover committed/generated fixture behavior where practical, read-only and
      mutation cases, deterministic checks, and semantic rubric checks.
- [ ] Run at least one target/no-skill comparison per representative skill.
- [ ] Use independent starting workspaces per case × condition × repetition.
- [ ] Hold harness mode and permissions constant across target/baseline unless
      mode sensitivity is the declared experiment; record whether each mode was
      capable of the requested operation.
- [ ] Apply `skill-contract` only to target; apply `shared-outcome` and
      `universal-safety` fairly across conditions.
- [ ] Add one placebo comparison if it remains a thin Promptfoo configuration,
      not a custom framework project.

### M1.4 Revision comparison

- [ ] Demonstrate one `code-review` candidate/reference comparison using actual
      Git revisions.
- [ ] Hold task, fixture, harness/mode, model/reasoning profile, provider,
      tools, permissions, system/agent profile where relevant, and assertions
      constant or materially equivalent.
- [ ] Record candidate/reference SHAs, skill hashes, fixture hash, case identity,
      and Promptfoo version.
- [ ] Verify candidate/reference starting target content is identifiable and
      does not silently depend on unknown dirty or untracked local state.
- [ ] Do not attribute a difference to the skill revision when materially
      behavior-changing execution-profile dimensions differ, including a known
      resolved-backend difference unless shown immaterial; report such runs as
      portability, coverage, or an intentional interaction experiment.
- [ ] Avoid rebuilding a generic regression runner.

### M1.5 Frozen holdout

- [ ] Do not edit or tune against `review-discrim-1.json`.
- [ ] Stabilize development implementation before invoking holdout.
- [ ] Run one unchanged post-stabilization holdout evaluation.
- [ ] If infrastructure invalidates a run, record why and do not use observed
      model behavior to tune implementation/skills.
- [ ] If valid holdout behavior informs a skill, routing, evaluator, or expected
      outcome change, mark that holdout version `consumed`,
      `retired_for_holdout`, or equivalent before the next generalization claim.
- [ ] Report development and holdout separately.

### M1.6 Kilo evidence note/integration

- [ ] Use documented Kilo JSON/CLI behavior only.
- [ ] Capture output, errors, tokens, latency, model, repeat, and session identity
      when available.
- [ ] Classify activation evidence as native, heuristic, forced, behavioral, or
      none/unknown.
- [ ] Keep forced activation as Layer B evidence.
- [ ] Keep Layer C `not_run`/limited unless actual Kilo evidence meets the
      definition.
- [ ] Identify which Kilo functionality should be proposed upstream to
      Promptfoo.

### M1.7 v1/v2 comparison and report

- [ ] Compare overlapping routing prompts, labels, outputs, failures,
      repetitions, metrics, fixtures, condition identity, assertions, and
      provenance.
- [ ] Classify each material difference as expected engine difference,
      Promptfoo limitation, v1 limitation, prototype bug, model nondeterminism,
      provider/harness difference, or unknown.
- [ ] Produce `experiments/promptfoo/REPORT.md` with one of: `YES`,
      `YES, WITH MATERIAL GAPS`, `NO`, `INCONCLUSIVE`.
- [ ] Include file-by-file future disposition and measured code-deletion
      estimate.
- [ ] State exactly what remains custom and why.
- [ ] Run the repository gate and Promptfoo spike tests/config validation.

### M1.8 Required fresh-context review

- [ ] Launch the repository-required fresh read-only adversarial reviewer before
      any push.
- [ ] Review for unnecessary wrappers, duplicated provider/assertion/reporting
      logic, holdout leakage, baseline unfairness, failure/null conflation,
      workspace contamination, unsupported Layer C claims, provenance gaps, and
      benchmark tuning.
- [ ] Apply findings only in a separately authorized change pass.
- [ ] Address material high-confidence defects. If those fixes materially change
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

### Decision review

- [ ] Verify all M1 results are protocol-usable at their claimed level.
- [ ] Quantify generic machinery Promptfoo replaces using actual lines/files.
- [ ] Quantify custom code retained by category: corpus conversion, metrics,
      policy, provenance, workspace, Git target, Kilo, strict isolation.
- [ ] Determine whether custom code is thin or a disguised parallel framework.
- [ ] Verify remaining custom code is demonstrably limited to AGK-specific
      semantics, corpus conversion, provenance, workspace controls, and genuine
      provider gaps.
- [ ] Ask whether observed v1/v2 differences are attributable to
      execution-profile changes rather than evaluator behavior.
- [ ] Verify Promptfoo caching/retry behavior preserves AGK evidence semantics.
- [ ] Verify the design avoids universal-score assumptions and keeps materially
      different profiles visible.
- [ ] Verify unknown or unverified runtime semantics remain unknown and exact
      raw provider/harness settings are preserved.
- [ ] Review unresolved v1/v2 differences and unknowns.
- [ ] Review Promptfoo dependency/maturity risks and version-pinning strategy.
- [ ] Decide repository name and migration provenance approach.

### Decision branches

#### `GO`

- Promptfoo absorbs the clear majority of commodity mechanics.
- Remaining custom code expresses AGK semantics or a real provider gap.
- M3 is authorized.

#### `GO WITH MATERIAL GAPS`

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

## M3 — Create `agent-guidance-kit-evals` foundation

**Objective:** Establish an independent Promptfoo-backed project that targets an
external, still-intact AGK checkout.

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

### Deliverables

- Per-skill eval packs under eval-repo corpus.
- Development confusion sets and physically separate holdout.
- Target profile mapping corpus skill identities to external target skills.
- Historical schema-v3 results, summaries, validation matrix, routing reports,
  and frontmatter inventory under `historical-v1`.
- `MIGRATION.md` with source repository, commit, extraction date, path mapping,
  and known provenance gaps.
- Hash comparison showing fixtures/suites remained stable where intended.

### Exit criteria

- Canonical corpus has one owner.
- Generated Promptfoo projections are reproducible and not hand-maintained.
- Historical invalid/limited/not-run labels remain unchanged.
- Holdout content and identity match the frozen source.

## M5 — Establish thin Promptfoo/Kilo integration

**Objective:** Productize only the custom surface demonstrated necessary by M1/M2.

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
| 2026-08-23 | Separate the portable skill library from evaluation ownership. | proposed | Full shared conversation. |
| 2026-08-23 | Do not build a new generic evaluator by default; evaluate Promptfoo as engine. | proposed, gated | Landscape/code-level comparison and compatibility-spike specification. |
| 2026-08-23 | Preserve AGK corpus/methodology/provenance/Kilo integration in a thin eval repository. | proposed | Parent architecture. |
| 2026-08-23 | Keep evaluator v1 intact until Promptfoo equivalence is demonstrated. | active constraint | M1 spike requirements. |
| 2026-08-23 | Treat evidence as sparse facts interpreted by policy, not certification. | proposed | Later evidence/confidence discussion. |

## Immediate next actions

1. Review this corrected architecture against the intended product direction.
2. Let the active Promptfoo agent finish M1 without changing the skills,
   holdout, or evaluator v1.
3. Review `REPORT.md`, v1/v2 evidence, tests, and adversarial review record.
4. Make and record the explicit M2 go/no-go decision before creating or cleaning
   any repository.
