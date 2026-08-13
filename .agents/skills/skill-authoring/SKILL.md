---
name: skill-authoring
description: >-
  Author or revise a repository-local agent skill after explicit approval,
  preserving its trigger, boundaries, portability, and validation contract. Use
  when creating, extending, restructuring, or applying an approved skill change.
---

# Skill Authoring

Use this skill to implement an approved change to a project-local skill. It owns
edits and validation; it does not replace a content review or a structural audit.

## Keep the roles distinct

| Skill | Owns |
| :--- | :--- |
| **skill-authoring** | Approved skill edits and their validation |
| `skill-reviewer` | Content recommendations; report-only by default |
| `rules-and-skills-audit` | Structure, overlap, routing, and drift findings |
| `skill-optimizer` | Context-cost reduction and its preservation checks |
| `harness-adaptation` | Harness capability profiles and thin projections |

Do not turn a domain skill into a generic coding procedure, an unrelated
harness adapter, or a second copy of canonical project policy. A skill whose
distinct purpose is harness adaptation follows the neighboring owner above.

## Before editing

Write down the smallest contract:

- **Trigger:** the request that should route here, plus a nearby request that should not.
- **Owner and non-goals:** what this skill decides and what remains elsewhere.
- **Inputs and outputs:** files, evidence, edits, report, or handoff required.
- **Side effects:** every file or external system that may change.
- **Stop condition:** the exact approval or evidence needed to finish.

If the trigger, owner, and completion contract are not distinct from an existing
skill, extend that skill instead of inventing another one. An approval to edit a
named skill does not authorize unrelated guidance, index, or runtime changes.

## Workflow

1. Read the repository's applicable rules, the current skill, its index entry,
   and adjacent skills. Inspect the current worktree before deciding scope.
2. Keep the canonical file at `.agents/skills/<name>/SKILL.md`. The directory
   name, frontmatter `name`, and index entry must agree.
3. Draft a short, routeable description followed by purpose, boundaries,
   decision points, stop conditions, and verification. Keep the body below
   roughly 500 lines; move rare detail to a directly linked sibling reference.
4. Preserve portability. Use repository-relative examples and generic tool
   language. Do not add credentials, private data, personal paths, provider
   catalogs, vendor metadata, or network-dependent behavior.
   When editing this kit, classify the change as portable core, target-local
   adaptation, or evidence-only material. Keep product names, stack-specific
   commands, provider/model policy, local paths, and target migrations out of
   reusable core guidance; preserve those only in clearly labeled evidence or
   the consumer project.
5. Apply only the explicitly approved files and findings. Do not overwrite
   unrelated guidance, create duplicate skill bodies, add unrequested harness
   projections, commit, publish, or send external messages unless separately
   authorized. Update required metadata when the repository's established
   validator and discovery contract require it.

## Validate before handoff

- Parse the frontmatter and confirm the name, description, and non-empty body.
- Test routing with one matching request, one neighboring request, and one
  ambiguous request with a stated tie-breaker.
- Check every relative link and referenced script or option against the current
  tree. Remove unverifiable claims and unfinished placeholders.
- For a new or materially changed skill, use
  [skill-evaluation](../skill-evaluation/SKILL.md) to compare matching,
  neighboring, and ambiguous cases before claiming that it improves outcomes.
- Check the diff for whitespace errors, secrets, personal paths, provider
  assumptions, unintended files, and changes outside the approved scope.
- Re-read the complete changed skill and report exactly what was validated,
  skipped, or blocked. Leave release actions to their separately approved flow.

Completion means the approved skill is coherent, portable, routeable, and
validated; it does not imply approval for a broader playbook rewrite.
