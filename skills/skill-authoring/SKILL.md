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

## Calibrate instruction rigidity

Match how prescriptive the skill is to the task's risk and variability. Both
over- and under-specifying cause failures:

- **Flexible heuristics** for work with several valid approaches. State the goal
  and the trade-offs; let the agent judge. Reserve rigid steps for when they earn
  their cost.
- **Structured procedures** when a preferred sequence measurably reduces mistakes
  (order-dependent builds, multi-step migrations, safety-critical setups). Name
  the required order and the checkpoint that gates the next step.
- **Deterministic scripts/tools** for fragile, repetitive, or failure-sensitive
  operations (parsing, checking, transforming). A script removes ambiguity and
  lowers context cost, but keep it network-free, standard-library, and covered by
  tests per the [companion script hygiene](#validate-before-handoff) rules.

Connect rigidity to the rest of this skill:

- *Context cost:* deterministic scripts and tight procedures shrink the reasoning
  an agent must do; spend that saved budget on the parts that still need judgment.
- *Progressive disclosure:* push rare, rigid detail into a `references/` file so
  the common path stays flexible; do not pad the entrypoint with ceremony.
- *Degrees of freedom:* prescription level is the main lever for how much freedom
  the agent keeps. Choose it deliberately, not by habit.

Two failure modes to avoid:

- **Unnecessary ceremony:** do not convert judgment-heavy work (design, triage,
  review) into checklists that pretend a hard call is a procedure.
- **Underspecified danger:** do not leave destructive, security-sensitive, or
  irreversible operations as vague advice. Pin them to exact commands, guards, and
  approval gates.

## Workflow

1. Read the repository's applicable rules, the current skill, its index entry,
   and adjacent skills. Inspect the current worktree before deciding scope.
2. Keep the canonical file at `skills/<name>/SKILL.md`. The directory
   name, frontmatter `name`, and index entry must agree.
3. Draft a short, routeable description followed by purpose, boundaries,
   decision points, stop conditions, and verification. Make the entrypoint a
   table of contents for the common path, keep the body below roughly 500
   lines, and move rare detail to a directly linked sibling reference. Include
   trigger phrases and a neighboring-task tie-breaker in the description or
   body; do not rely on a global name or a long index to route the skill.

   **Description and routing formula:**
   Draft the YAML frontmatter `description` using this 3-part structure (100–300 characters recommended; must be 40–1024 characters):
   1. *Action & Scope:* Active verb stating what the skill does (e.g., "Harden correctness through a bounded QA loop...").
   2. *Positive Triggers:* Explicit user query phrases and situations where this skill must activate (e.g., "Use when asked to investigate flaky tests, coverage gaps, or edge cases...").
   3. *Negative Boundary:* Explicit tie-breaker routing adjacent requests away (e.g., "Do not use for general code review (use code-review) or architectural redesign (use architecture-review).").
   Avoid generic filler phrases ("Helps with tasks", "Manages files", "Improves code") that match indiscriminately.

   **Reference file conventions:**
   When moving low-frequency detail or deep specifications into sibling references:
   - Place reference files under `skills/<name>/references/<topic>.md`.
   - Keep the common-path decision tree, core contract, and primary checklist in the main `SKILL.md` (< 500 lines).
   - Link references using relative paths (e.g., `[topic title]` targeting `references/<topic>.md`).
   - Ensure each reference is a self-contained deep dive with clear headings, not an orphaned fragment or a duplicate copy of the main workflow.

4. Preserve portability. Use repository-relative examples and generic tool
   language. Do not add credentials, private data, personal paths, provider
   catalogs, vendor metadata, or network-dependent behavior.
   When editing this library, classify the change as portable core, target-local
   adaptation, or evidence-only material. Keep product names, stack-specific
   commands, provider/model policy, local paths, and target migrations out of
   reusable core guidance; preserve those only in clearly labeled evidence or
   the consumer project. Confirm that the canonical skill remains the sole
   source of truth and that no harness projection or sibling name collision
   creates a second authority.

   **Companion script hygiene:**
   When a skill includes deterministic helper scripts (under `scripts/`):
   - Write scripts in standard-library Python (or zero-dependency POSIX shell) without undeclared external package requirements.
   - Ensure scripts are completely network-free and execute deterministically.
   - Implement explicit guards against path traversal, symlink escapes, and unauthorized file writes outside the repository root.
   - Provide comprehensive automated unit tests in `tests/` covering both success paths and error conditions.

   **Harness-neutral syntax:**
   Canonical `SKILL.md` files must use pure, standard Markdown. Never include harness-specific syntax (such as `@`-mentions, XML tool execution blocks, or proprietary IDE metadata tags) in canonical skill bodies. Harness adaptations belong strictly in thin adapter projections managed by `harness-adaptation`.

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
- Check the entrypoint's context cost and move low-frequency detail behind a
  clear reference link when that preserves discoverability and verification.
- For a new or materially changed skill, treat clean-context evaluation in the
  [separate evaluation repository](https://github.com/HyperVon/agent-guidance-kit-evals)
  as an *optional validation gate you run yourself* when the change claims an
  outcome improvement. Do not hand the authoring task to evaluation, and do not
  impose a full evaluation project unless the user requested measurement.
- Check the diff for whitespace errors, secrets, personal paths, provider
  assumptions, unintended files, and changes outside the approved scope.
- Re-read the complete changed skill and report exactly what was validated,
  skipped, or blocked. Leave release actions to their separately approved flow.

Completion means the approved skill is coherent, portable, routeable, and
validated; it does not imply approval for a broader playbook rewrite.
