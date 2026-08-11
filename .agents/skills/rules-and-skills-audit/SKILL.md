---
name: rules-and-skills-audit
description: >-
  Audit agent rules, skills, and operating guidance for overlap, conflicts,
  unclear triggers, stale references, and consolidation opportunities. Use for
  structural or cross-repository guidance audits; use skill-reviewer instead
  when the main question is missing domain content.
---

# Rules And Skills Audit

Audit policy and task workflows before suggesting consolidation. Shared topics
are not proof of duplication: preserve deliberate safety reinforcement, thin
entrypoints, distinct audiences, and harness projections that point to a
canonical source.

## Audit workflow

1. Discover guidance with `rg --files --hidden`, including nested `AGENTS.md`,
   operating files, `CLAUDE.md`, skill files, harness rules, and instructions
   under common guidance directories. Respect each file's directory scope.
2. Build a compact inventory: path, purpose, scope, trigger, dependencies,
   source-of-truth claims, and notable rules or workflows. Record files read and
   candidates skipped with reasons.
3. Read the actual files behind links, then compare for:
   - repeated policy or checklists with one clear owner;
   - overlapping triggers or broad workflows that subsume narrow ones;
   - contradictory commands, thresholds, or approval rules;
   - stale, broken, unreachable, or orphaned references;
   - missing boundaries between always-on rules and conditional procedures.
4. Classify each finding as `duplicate`, `merge candidate`, `scope/trigger issue`,
   `stale/inaccurate`, `conflict`, or `improvement`. Cite the exact path and
   heading or line, explain the evidence, and rank impact and risk.
5. Recommend the smallest reversible change. Name the canonical owner, migration
   map, affected links, and validation required. Do not call word-frequency
   similarity semantic equivalence, and ignore illustrative fenced examples when
   checking links.

## Report shape

```markdown
# Guidance audit
## Inventory summary
## Findings
## Keep separate
## Proposed consolidation plan
## No-change conclusion
```

The report must say which files were reviewed, which were skipped, and whether
the evidence supports a change. For each proposed change include its trigger,
invariants, exceptions, approval boundary, and post-change checks.

## Apply boundary

An audit is read-only and report-first. Do not delete, merge, or rewrite
guidance while auditing. A later explicit approval may authorize named findings
or a bounded group; apply those edits through `skill-authoring`, then re-read
links, routing, and invariants. Never treat a general request to inspect or
optimize as approval for a sweeping rewrite.

Do not broaden this skill into content enrichment, documentation fact-checking,
application-code review, provider selection, or worker supervision.
