# Proposed catalog changes

Status: approved by the user and applied in the catalog authoring pass on
2026-08-13. The user additionally requested that evaluation baselines be real
independent fresh workers rather than role-played no-skill conditions; that
protocol wording is now applied. Dynamic comparisons under the strengthened
protocol remain pending; no external skill text or scripts were copied or
executed.

## Protocol audit note

An attempted GPT-5.6 Luna / Max comparison was deliberately rejected. The
worker-visible prompt named neutral temporary directories, but the child-session
metadata showed the catalog checkout as the actual working directory; the
supposed baseline could read the catalog's skill evaluation files. This is
contamination, not a limitation to score around. No result or matrix mark was
created. Future runs require actual session cwd/workspace metadata and an
immediate visible-file manifest before task execution; a prompt-mentioned path
does not establish isolation. The harness also exposed the available skill
catalog in worker-visible system context, so future baselines must not receive
the target skill's identity, path, description, or injection metadata either.

## Isolated-runner canary

A protocol-valid one-skill canary was completed with Codex CLI `0.147.0-alpha.6.5`
using `gpt-5.6-luna` at `max` effort. It ran all three committed
`frontend-quality-review` cases as six distinct fresh sessions. Each guided
root contained the target skill at the neutral path
`.agents/skills/task-quality/SKILL.md`; each baseline root had a different
neutral `AGENTS.md` with no guidance reference and no `.agents` tree. Both
variants performed the same `pwd` and local-file preflight. Fixtures were
byte-identical, and session logs were captured outside the worker roots.

The parent verified the session IDs, actual cwd, visible manifests, skill hash,
fixture hashes, and absence of target/evaluation metadata in baseline traces
before grading the frozen assertions. The run was protocol-valid but did not
show a skill advantage on this smoke case set (6/9 assertions in each
condition), so it is recorded as `REVISE`, not as a passing `KEEP` result. No
full-catalog run was started.

This is the short decision memo derived from the [comprehensive discovery
ledger](./2026-08-13-comprehensive-skill-discovery.md). The proposals favor
small, evidence-backed improvements to existing owners, with only two likely
new skills. They are not recommendations to copy external skills wholesale.

## How to review

The marked decisions record the user's approval. An Adopt decision authorized
the separately scoped authoring/evaluation pass; it did not authorize external
publication, commits, pushes, or release actions.

## Recommended first batch

These are the changes I would do first because they have the strongest
behavioral evidence, clear existing ownership or a clear routing gap, and
relatively low catalog-expansion cost.

| ID | Proposal | Decision |
| --- | --- | --- |
| A1 | Improve `ai-slop-detector` | [x] Adopt  [ ] Defer  [ ] Reject |
| A2 | Improve `skill-optimizer` | [x] Adopt  [ ] Defer  [ ] Reject |
| A3 | Improve `code-review` | [x] Adopt  [ ] Defer  [ ] Reject |
| A4 | Improve `quality-hardening` | [x] Adopt  [ ] Defer  [ ] Reject |
| N1 | Add `frontend-quality-review` | [x] Adopt  [ ] Defer  [ ] Reject |
| N2 | Add `threat-modeling` | [x] Adopt  [ ] Defer  [ ] Reject |

### A1 — Strengthen `ai-slop-detector`

Add observable software-engineering and UI failure patterns:

- invented APIs, imports, flags, configuration, or test claims;
- swallowed exceptions, hidden fallbacks, unsafe casts, dead/TODO stubs,
  duplicate helpers, needless abstractions, and misleading comments;
- UI work that lacks product-specific intent, meaningful states, responsive
  behavior, keyboard/focus handling, reduced-motion behavior, or accessible
  contrast;
- a minimum-effective-edit rule that preserves voice, technical terms,
  uncertainty, and concrete facts.

Keep out: authorship detection, “AI-sounding” style judgments, universal
banned-word lists, and aesthetic preferences without a demonstrated defect.

Expected cost: small-to-medium body increase; likely reduced false-positive
slop findings if the evidence examples are kept compact and progressive.

Forward tests:

- Matching: “Audit this AI-generated patch for slop.”
- Neighboring: “Review this ordinary code diff.”
- Ambiguous: “Make this UI less generic.”

Success means the skill reports anchored defects and impact, not suspected
authorship or taste.

### A2 — Strengthen `skill-optimizer`

Add four explicit checks:

1. account for loaded skills, root instructions, tools, and references;
2. detect progressive-disclosure misses and routing ambiguity;
3. distinguish context poisoning, distraction, confusion, and instruction
   clash from ordinary duplication;
4. remove optimization machinery when before/after evaluation shows no useful
   behavior improvement.

Keep out: line-count targets, deletion of intentional safety reinforcement,
and optimization of guidance merely because it is verbose.

Expected cost: small body increase, with potential net context savings across
the catalog. This is the most important proposal for controlling the cost of
later additions.

Forward tests:

- Matching: “Reduce this skill’s context cost.”
- Neighboring: “Audit these skills for overlap.”
- Ambiguous: “Make this guidance clearer.”

Success means the skill measures and preserves triggers, ownership, approval,
safety, and verification rather than performing a prose rewrite.

### A3 — Strengthen `code-review`

Add review lenses that repeatedly appeared across independent collections:

- freeze a review point and separate contract/spec review from standards/style
  review;
- trace changed symbols through callers, removed behavior, sibling paths, and
  source-of-truth ownership;
- check whether tests have an independent oracle rather than merely exercising
  implementation details;
- maintain a coverage/disposition ledger and fail closed on unreviewed scope
  or unverified blockers.

Keep out: automatic implementation of findings, mandatory subagents, and
provider-specific review CLIs.

Expected cost: medium body increase; no new routing entry.

Forward tests:

- Matching: “Review this pull request.”
- Neighboring: “Review this one function for style.”
- Ambiguous: “Is this reviewer’s comment correct?”

Success means every finding and uncovered area has an evidence-backed status.

### A4 — Strengthen `quality-hardening`

Add test-selection guidance for:

- public-seam tests with independent oracles and red-before-green flow;
- characterization tests before changing legacy behavior;
- property-based or mutation tests when example tests can remain tautological;
- fresh reruns of the original reproduction and relevant gates.

Keep out: percentage-only coverage goals, mandatory mutation testing, and
framework-specific test commands.

Expected cost: medium body increase; high correctness value.

Forward tests:

- Matching: “Harden the regression coverage for this bug.”
- Neighboring: “Refactor this safely.”
- Ambiguous: “Increase test coverage.”

Success means the agent chooses an independent confidence-building probe,
not merely more lines executed.

### N1 — Add `frontend-quality-review`

Create a distinct report-only owner for explicit UI/frontend/UX/accessibility
quality reviews.

Contract:

- Input: UI scope, product/user/job intent, available design references, and
  the target viewport/platform assumptions.
- Output: prioritized findings with evidence and an acceptance/handoff list.
- Workflow: establish the design contract; inspect hierarchy, navigation,
  interaction states, responsive behavior, keyboard/focus behavior, reduced
  motion, contrast, typography, images, and performance; distinguish product
  defects from optional taste.
- Non-goals: net-new UI implementation, generic visual redesign, browser
  automation, and automatic screenshot acceptance without fresh evidence.
- Stop condition: report missing intent, unavailable screenshots, or untested
  states as evidence gaps rather than guessing.

Why separate: UI state/accessibility/interaction review is currently spread
across general quality and AI-slop guidance, with no clear owner or trigger.

Expected cost: one new skill plus evaluations; moderate routing cost, offset
by fewer broad `ai-slop-detector` activations.

Forward tests:

- Matching: “Review this dashboard UI for quality and accessibility.”
- Neighboring: “Build a new page from this brief.”
- Ambiguous: “Make this page prettier.”

### N2 — Add `threat-modeling`

Create a distinct report-only owner for explicit design-time threat modeling.

Contract:

- Input: repository or system scope, deployment/exposure assumptions, assets,
  actors, and known trust boundaries.
- Output: repository-grounded threats/abuse paths, likelihood/impact,
  assumptions, existing mitigations, recommended mitigations, and coverage
  gaps.
- Workflow: map components and entrypoints; separate runtime from CI/dev/test;
  identify boundaries, assets, attacker capabilities and non-capabilities;
  enumerate realistic abuse paths; validate assumptions; check that every
  boundary and entrypoint is represented.
- Non-goals: unrestricted penetration testing, live probing, compliance
  certification, or ordinary vulnerability review.
- Stop condition: pause for missing context or label assumptions explicitly.

Why separate: the current `security-review` skill explicitly excludes being a
substitute for a product-specific threat model, and the official OpenAI source
uses a clearly distinct explicit trigger.

Expected cost: one new skill plus evaluations; high routing clarity and strong
security value.

Forward tests:

- Matching: “Threat-model this API using trust boundaries and abuse paths.”
- Neighboring: “Review this authentication change for vulnerabilities.”
- Ambiguous: “Is this architecture secure?”

## Recommended second batch

These are worthwhile, but I would wait until the first batch has evaluations
because they either have more overlap or require a broader workflow decision.

| ID | Owner or candidate | Proposed change | Decision |
| --- | --- | --- | --- |
| B1 | `skill-authoring` + `harness-adaptation` | Keep entrypoints as compact tables of contents; move rare detail to references; require trigger phrases, source-of-truth ownership, body-cap awareness, collision checks, and harness round-trip verification. | [x] Adopt  [ ] Defer  [ ] Reject |
| B2 | `systematic-debugging` | Add reproduce/minimize → ranked falsifiable hypotheses → one-variable instrumentation → condition-based wait/performance baseline → seam regression → original reproduction rerun. | [x] Adopt  [ ] Defer  [ ] Reject |
| B3 | `security-review` | Add false-positive disproof, explicit non-capabilities, insecure-default/fail-open analysis, and structured supply-chain risk signals. | [x] Adopt  [ ] Defer  [ ] Reject |
| B4 | `dependency-upgrade` | Add yanked/deprecated/abandoned package, install-script/binary, publisher-concentration, provenance, advisory, and expand/contract migration checks. | [x] Adopt  [ ] Defer  [ ] Reject |
| B5 | `reduce-code-size` | Add characterization, scope allowlists, checkpoints, handoffs, waivers, and behavior-parity evidence; reject line count as sole success metric. | [x] Adopt  [ ] Defer  [ ] Reject |
| B6 | `skill-evaluation` | Separate static budget checks, semantic judging, clean-context routing probes, repeated-run evidence, and portability/round-trip checks. | [x] Adopt  [ ] Defer  [ ] Reject |
| B7 | `catalog-discovery` | Make popularity-led recursive discovery, canonical-origin tracing, license/revision capture, duplicate-origin deduplication, and unavailable-source reporting explicit. | [x] Adopt  [ ] Defer  [ ] Reject |

## Candidates I would not add yet

| Candidate | Recommendation | Reason |
| --- | --- | --- |
| `implementation-planning` | Defer | Useful and distinct from architecture review, but first determine whether planning belongs in this catalog or in project-local workflows. |
| `review-feedback-reconciliation` | Defer | Real trigger gap, but test whether `code-review` can own review-comment intake without a new skill. |
| `release-readiness` | Defer; enhance Git workflow first | Strong behavior, but a separate owner may duplicate release/PR gates. |
| `issue-triage` | Defer; consider Git workflow extension | State-machine pattern is good, but it is coupled to issue-tracker mutation and maintainer policy. |
| `observability-hardening` | Defer | Valuable for production teams, but currently less distinct from debugging, security, and operations guidance. |
| `schema-migration-safety` | Defer | High value but provider-specific evidence dominates; first generalize the behavior into dependency, quality, and architecture owners. |
| Large React/Next/Vercel/cloud/browser/mobile/MCP packs | Reject for this catalog | Project- and provider-specific; would add substantial routing and context cost. |
| Generic “engineering best practices” mega-skill | Reject | Duplicates existing owners, weakens routing, and conflicts with the optimizer’s progressive-disclosure goal. |

## Proposed implementation order after approval

1. Evaluate A1–A4, N1, and N2 in clean context using the listed probes.
2. Author only approved items, preserving current report-only and approval
   boundaries.
3. Run the catalog’s full validation and routing checks.
4. Re-run the optimizer inventory and compare context cost, activation
   precision, false triggers, and evidence completeness.
5. Apply the second batch only where the evaluations show a measurable delta.

## Evidence anchors

- [AI slop and code-quality sources](https://github.com/petergyang/no-ai-slop/blob/d30eddb9e04562234f2070b5ee63ca4649d9a05e/skills/no-ai-slop/SKILL.md)
- [Anti-UI-slop source](https://github.com/github/awesome-copilot/blob/55b952d2f9bd5b092d2f4b87fdbcf205a1a5ccc5/skills/anti-ui-slop/SKILL.md)
- [OpenAI threat-model source](https://github.com/openai/skills/blob/49f948faa9258a0c61caceaf225e179651397431/skills/.curated/security-threat-model/SKILL.md)
- [Matt Pocock engineering skills](https://github.com/mattpocock/skills/tree/84fdeffd12f2ee307994d1eb6feb48173b6e0502)
- [Qwen evidence-led code review](https://github.com/QwenLM/qwen-code/blob/52cfb189723325c860e6c732653224e8cb38f900/packages/core/src/skills/bundled/review/SKILL.md)
- [Wshobson authoring and evaluation guidance](https://github.com/wshobson/agents/blob/c4b82b0ad771190355eb8e204b1329732a18449a/docs/authoring.md)
- [Agent Skills dependency-manifest proposal](https://github.com/agentskills/agentskills/discussions/210)
