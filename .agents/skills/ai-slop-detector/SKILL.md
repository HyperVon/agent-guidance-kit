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
authorship, intent, or tool use. Default to audit-and-report: do not edit
anything unless the user explicitly asks to clean up, fix, or remove findings.
When cleanup is authorized, make only the smallest safe corrections in scope.

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

Every finding needs an anchor (path, line, diff, check, contract, or
reproduction), the actual or credible impact, the smallest safe correction or
reason to defer, and a severity based on impact rather than suspected origin.
Separate observations, inferences, and unknowns.

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
   source. Do not infer motive.
5. **Report findings.** Prefer a short list of concrete findings over a
   list of suspicions. Include strengths or explicit non-issues when they
   prevent unnecessary churn.
6. **If cleanup was explicitly requested,** apply only validated corrections,
   preserve unrelated work, and rerun checks that cover each correction.

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
