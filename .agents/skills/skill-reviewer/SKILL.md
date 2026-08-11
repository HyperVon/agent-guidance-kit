---
name: skill-reviewer
description: >-
  Review agent skills and project guidance for missing, weak, or misleading
  content and recommend concrete improvements. Use for skill reviews, guidance
  enrichment, agent-file audits focused on content, or workflow meta-review;
  recommend only unless the user explicitly asks to apply selected findings.
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

Choose one mode:

- **content** (default): spend most effort drafting missing guidance.
- **meta**: inspect routing, indexes, links, and discoverability.
- **full**: do both, with content findings still primary.

Do not make a content review into a cosmetic description rewrite. Treat an
explicit request to review as permission to inspect, not permission to edit.

## Review workflow

1. Define the mode, bounded paths, and any skipped candidates.
2. Read the actual rules, skill bodies, references, tests, and source files that
   the guidance claims to govern. Do not infer a gap from filenames alone.
3. Ask: what would a capable engineer still get wrong after following only this
   guidance? Look for boundaries, correctness, security, concurrency,
   persistence, testing, operability, and readability traps that matter here.
4. Draft paste-ready additions: a decision rule, anti-pattern, example,
   checklist, or short reference section. Prefer teachable specifics over
   generic best practices. Keep always-loaded skills concise.
5. In `meta` or `full` mode, check weak triggers, broken links, orphaned entries,
   duplicate workflows, and stale projections as secondary findings.
6. Stop after the report. If the user selects findings, name the exact approved
   paths and hand implementation to `skill-authoring`.

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
