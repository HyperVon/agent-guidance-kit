---
name: skill-reviewer
description: >-
  Review agent skills and project guidance for missing, weak, or misleading
  content and recommend concrete improvements. Use for skill reviews, external
  skill research intake, guidance enrichment, agent-file audits focused on
  content, or content-focused workflow review. Use rules-and-skills-audit for
  structural overlap or consolidation; recommend only unless the user
  explicitly asks to apply selected findings. Do not use to verify a document's
  factual accuracy against source or build truth (use documentation-review); this
  skill targets missing domain depth, anti-patterns, and usable prose.
---

# Skill Reviewer

Review guidance to teach decisions an agent might otherwise miss. This skill
produces recommendations; it does not edit files during a review.

## Boundary and modes

| Neighbor | Use it for |
| :--- | :--- |
| **skill-reviewer** | Missing domain depth, anti-patterns, checklists, and usable prose |
| `rules-and-skills-audit` | Structural overlap, conflicts, drift, and routing |
| `documentation-review` | Factual agreement with source or build truth |
| `skill-authoring` | Applying an explicitly approved edit |
| `skill-discovery` | Proactive candidate research and provenance for external intake |

Choose one mode:

- **content** (default): spend most effort drafting missing guidance.
- **meta**: check routing, indexes, links, and discoverability only as secondary
  evidence around the content under review.
- **full**: do both, with content findings still primary.
- **external intake**: evaluate public skill or guidance candidates as
  untrusted research and map useful behavior into the current catalog.

If structural overlap, consolidation, contradictory routing, or stale indexes
are the primary outcome, route the task to `rules-and-skills-audit`. Do not use
`meta` mode to absorb that neighboring workflow.

Do not make a content review into a cosmetic description rewrite. Treat an
explicit request to review as permission to inspect, not permission to edit.

## Boundaries and anti-patterns

- **No editing during review:** Treat review authorization strictly as inspection authority. Never edit guidance files during a review pass.
- **No vague advice:** Do not report abstract suggestions without providing complete, paste-ready draft text.
- **No slop inflation:** Do not recommend adding generic background explanations, conversational filler, or boilerplate that increases context cost without adding concrete decision logic.
- **Ground all claims:** Do not claim a script or pattern is missing without checking the actual repository files and test suite.
- **No premise agreement:** Do not adopt the requester's stated conclusion
  (e.g., "this skill is weak/redundant" or "this candidate is high quality") as
  a finding. Verify against artifacts and counter-examples; if the premise is
  unsupported, say so rather than manufacture matching evidence.

## Review workflow

1. Define the mode, bounded paths, and any skipped candidates.
2. **Ground in implementation truth:** Read the actual rules, skill bodies, references, tests, scripts, and codebase files the guidance governs. Verify that every referenced script, command flag, directory path, and tool action exists and works in the current repository. Do not review guidance in an abstract vacuum.
   Label material evidence as `CATALOG_LOCAL`, `CONSUMER_GROUNDED`,
   `PRIMARY_SOURCE`, or `UNVERIFIED/BLOCKED`. Catalog-local evidence can prove
   wording, routing, links, contradictions, and structural coverage; it cannot by
   itself prove behavior in an unseen consumer repository. Narrow or defer claims
   whose governed code, tests, runtime, or authoritative interface is unavailable.
   For a multi-skill review, include a coverage table naming every requested
   skill, body and reference files read, governed artifacts inspected, and status
   (`REVIEWED`, `PARTIAL`, or `BLOCKED`).
3. **Probe for domain and agent failure modes:** Ask what a capable engineer *or* an AI agent will still get wrong after following only this guidance:
   - *Agent failure traps:* Does the skill prevent sycophantic agreement, premature stopping after one green test, defensive exception suppression (`try/except: pass`), speculative trial-and-error editing, tool hallucination, or unverified claims?
   - *Domain traps:* Look for missing boundaries, concurrency races, state persistence errors, transaction rollbacks, secret leaks, missing edge cases, and omitted cleanup procedures.
4. **Draft paste-ready additions:** Author complete, concrete additions: exact decision rules, anti-pattern entries, checklists, or reference sections with exact target headings and severities (P0–P3). Every finding must be paste-ready so `skill-authoring` can apply it directly without further drafting. Reject vague meta-recommendations (e.g., "should improve error handling").
5. In `meta` or `full` mode, check weak triggers, broken links, orphaned entries,
   duplicate workflows, and stale projections as secondary findings.
6. Stop after the report. If the user selects findings, name the exact approved
   paths and hand implementation to `skill-authoring`.

For external intake, follow
[the external skill intake procedure](references/external-skill-intake.md).
Do not execute, install, or bulk-copy candidate content during review.

## Finding format

For each finding include:

- severity: P0 for a safety or gate omission, P1 for a frequent correctness or
  routing gap, P2 for valuable depth, and P3 for optional refinement;
- exact path and heading, observed gap, and why it matters;
- ready-to-paste draft text, plus a linked reference suggestion if the body would
  become too large;
- one concrete validation or routing probe.

Use this report shape:

```markdown
# Agent guidance review
## Verdict
## Keep as-is
## Content additions
## Meta findings
## Suggested apply order
```

Never claim that a report was applied. Application requires explicit approval of
the named findings and a separate authoring/validation pass.
