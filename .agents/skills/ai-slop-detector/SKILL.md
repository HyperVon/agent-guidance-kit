---
name: ai-slop-detector
description: >-
  Audit repository artifacts for evidence-backed quality defects that appear
  plausible but add correctness, maintenance, safety, or review cost. Use for
  AI-slop, de-slopping, invented API or configuration claims, misleading tests
  or documentation, needless complexity, or a broad artifact-quality audit.
  Modify artifacts only when the user explicitly requests cleanup.
---

# Evidence-Based AI-Slop Audit

## Authority and scope

Treat slop as an observable artifact-level deficit, never as evidence about
authorship, intent, or tool use. Emoji, verbosity, unusual formatting, or provider
signals are investigation prompts, not evidence of defect or authorship. Default to audit-and-report: do not edit
anything unless the user explicitly asks to clean up, fix, or remove findings.
When cleanup is authorized, make only the smallest safe corrections in scope.

When this hierarchy is adopted, keep the compact evidence-first quality
baseline in the target's canonical always-on operating guidance (normally
`.agents/OPERATING.md`). This skill owns the deeper procedure when a request
explicitly concerns AI slop, evidence-backed artifact quality, or a broad
cross-artifact audit. Do not load or copy this full audit merely to get the
baseline, and do not broaden an ordinary implementation task into a full audit
without evidence or a matching request.

Review the requested repository, diff, subsystem, or artifact and the relevant
source of truth. Depending on scope, this can include source, tests,
documentation, skills, rules, configuration, build files, generated artifacts,
and diffs. Do not broaden the review merely because another artifact is easy
to inspect.

## Neighboring skills

- `code-review` owns focused diff or subsystem review;
  use this skill instead for cross-artifact quality and evidence problems.
- `architecture-review` owns redesign and
  refactor-versus-keep recommendations.
- `documentation-review` owns a full factual
  documentation audit against source.
- `rules-and-skills-audit` owns structural
  consolidation, overlap, and routing conflicts in guidance.
- `skill-reviewer` owns missing domain depth in a
  skill; use this skill when the concern is an evidence-backed defect instead.
- `reduce-code-size` owns behavior-preserving
  simplification after a validated size or complexity goal.

Use one owner skill when it fully covers the request. Combine skills only when
the user asks for both scopes.

## Evidence standard

Report a finding only when an observable deficit is established by one or more
of these, in descending strength:

1. A failing check, reproduction, unsafe behavior, broken flow, or parse/link
   failure.
2. A conflict with a verified contract, source behavior, configuration schema,
   public interface, test requirement, or repository rule.
3. A local inconsistency with a demonstrated maintenance or correctness cost,
   such as duplicate mechanisms, a bypassed boundary, or dead instructions.

Style, verbosity, unusual formatting, artifact size, or formulaic language is
only an investigation prompt. Do not call it a defect without evidence.
Likewise, documentation placement is a finding only when internal rationale or
repeated exclusions demonstrably obscure user tasks, displace setup and usage,
or duplicate a more appropriate canonical design or security document.

Every finding needs an anchor (path, line, diff, check, contract, or
reproduction), the actual or credible impact, the smallest safe correction or
reason to defer, and a severity based on impact rather than suspected origin.
Separate observations, inferences, and unknowns.

## Observable quality patterns

Use these as investigation prompts, then verify them against the relevant
source of truth. Do not report a pattern merely because it is common in
generated artifacts:

- invented imports, APIs, flags, configuration, dependencies, or test claims;
- **Tautological and Mirror Tests:** Tests that assert mock return values against mocks (`expect(mock).toHaveBeenCalled()`) without validating system state transformations, or assertions that pass unconditionally (e.g., asserting `is not None` on a non-nullable return type);
- **Swallowed Exceptions and Phantom Fallbacks:** Blanket `try ... catch: pass` or returning empty dictionaries/null upon exceptions, concealing network or database failures and causing data corruption downstream;
- **Ghost Configuration and Phantom CLI Flags:** Configuration keys, environment variables, or CLI arguments parsed into options objects but never referenced or evaluated in execution logic;
- **Hallucinated Kwargs and Method Signatures:** Invoking standard library or third-party methods with non-existent keyword arguments that are silently absorbed by `**kwargs` without effect;
- **Circular / Duplicate Type Definitions:** Redundant parallel type declarations across multiple modules instead of consuming the canonical schema;
- dead or placeholder branches, duplicate helpers, and abstractions without a demonstrated consumer or outcome-level verification;
- comments and documentation that narrate obvious code, conceal uncertainty,
  or state behavior not established by source and checks;
- UI changes with no product/user/job intent, missing loading/empty/error/
  success/disabled/permission states, broken focus or keyboard behavior,
  inaccessible contrast, or unverified responsive and reduced-motion behavior.

For UI findings, distinguish a product or interaction defect from an optional
visual preference. Route a dedicated frontend/accessibility review to
`frontend-quality-review` when it needs a complete UI quality pass.

## Workflow

1. **Establish scope and mode.** Record the requested inputs, relevant local
   rules, source-of-truth artifacts, and whether the task is audit-only or an
   explicitly authorized cleanup.
2. **Inspect the complete scoped surface.** Read the diff before searching
   broadly. Include related tests, configuration, generated files, docs, and
   guidance when they can change the contract or outcome.
3. **Run proportionate local checks.** Prefer existing repository checks for
   parsing, compilation, tests, lint, links, schemas, and skill frontmatter.
   Treat an unrun check as a verification gap, not a passing result.
4. **Test the claim.** Verify APIs, flags, paths, dependencies, contracts,
   test independence, error handling, and boundary ownership against current
   source. For a framework, toolkit, or generator, run or trace the smallest
   primary consumer flow and compare its files, configuration, dependencies,
   and context burden with the recurring need it claims to solve. Check whether
   tests prove that outcome or only prove internal schemas and abstractions, and
   whether reference-project concepts leaked into generic behavior without an
   unrelated-target justification. For code and UI, inspect relevant states and
   failure paths rather than applying a style blacklist. Do not infer motive.
5. **Report findings.** Prefer a short list of concrete findings over a
   list of suspicions. Include strengths or explicit non-issues when they
   prevent unnecessary churn.
6. **If cleanup was explicitly requested:**
   - Make atomic, minimal corrections isolated by defect category (e.g., remove dead branches in one edit; fix swallowed exceptions in another).
   - Never bundle functional enhancements, stylistic reformatting, or architectural renames into a de-slopping cleanup.
   - Run the repository's relevant test suite after each atomic correction to prove zero behavioral regressions.

## Severity

Use the smallest severity that matches the demonstrated outcome:

- **P0:** credible destructive, security, data-loss, or unsafe external-action
  risk, or an invented integration that can cause such harm.
- **P1:** broken build, contract, lifecycle, boundary, or required behavior.
- **P2:** demonstrated misleading content, duplicate mechanism, needless
  complexity, weak test protection, or stale/broken guidance.
- **P3:** reviewability or style issue without demonstrated correctness or
  maintenance impact; normally defer rather than edit.

## Output and stop conditions

Return a report containing the scope and mode, verdict, findings with
`path:line`-style anchors, evidence, impact, correction or deferral,
verification status, and unresolved questions. For authorized cleanup, also
state the changed paths and checks run.

An audit has no file side effects. Cleanup may change only the explicitly
scoped artifacts and must not silently refactor adjacent code, weaken tests,
or invent tools, APIs, flags, dependencies, or configuration. Stop and report
an evidence gap when a finding cannot be verified, when a correction would
change behavior beyond the request, or when the issue belongs to a neighboring
owner skill.
