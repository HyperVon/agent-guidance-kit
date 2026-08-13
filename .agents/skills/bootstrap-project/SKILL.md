---
name: bootstrap-project
description: >-
  Inspect an existing software repository, compare its local agent guidance with
  this reusable skill library, and propose the smallest useful approval-gated
  integration. Use when starting agent guidance in a project, adopting this
  kit, selecting reusable skills, reconciling AGENTS or harness instructions,
  or reviewing whether a project would benefit from additional project-local
  skills. Report and plan by default; modify the target only after explicit
  approval of the exact adoption plan.
---

# Bootstrap a Project

Use the active coding harness and its current LLM to understand the target
project and choose guidance. Use bundled scripts only for mechanical facts,
hashes, dependency closure, receipt-aware application, and validation.

## Contract

- **Inputs:** target repository root, this kit's root, the user's objective, and
  all applicable target-local guidance.
- **Default output:** repository facts, guidance inventory, proposed selection,
  conflicts, integration edits, verification plan, and explicit approval gate.
- **Default side effects:** none. Inventory and proposal work are read-only.
- **Apply side effects:** install the maintenance entrypoint and approved
  dependency-closed skills, refresh only receipt-owned unmodified content,
  maintain a digest-guarded AGENTS route block, and then make any separately
  approved semantic guidance edits.
- **Stop conditions:** stop before mutation; stop on an unresolved collision,
  symlink, source drift, target drift, unclear canonical owner, secret exposure,
  or a material choice the user has not made.

Always include `agent-guidance-maintenance`; otherwise do not install every
skill. Do not add generic advice the base model already handles well. Do not
replace stronger project-local guidance.

## Hard boundaries

- Do not use a local LLM, embedded classifier, embeddings, or a separate
  semantic service. The active harness model performs selection and
  reconciliation.
- Do not fetch remote guidance during initial adoption, execute imported
  scripts, install packages, authenticate providers, start services, or inspect
  credentials/runtime data. An existing target may explicitly request the
  maintenance skill to refresh its already resolved, clean Agent Guidance Kit
  checkout; follow that skill's guarded source-refresh procedure rather than
  fetching arbitrary guidance.
- Do not add provider routing, quota policy, worker supervision, or model
  catalogs to the target.
- Do not overwrite, delete, rename, or silently merge locally modified target
  guidance. Receipt-owned adopted content may be refreshed only when its current
  digest still matches a prior receipt and the exact update plan is approved.
- Treat copied skills as target-local policy only after their content and
  integration have been reviewed and approved.

## Workflow

### 1. Establish roots and authority

Resolve the target repository and kit roots. Read the target's nested guidance
before interpreting it, including applicable `AGENTS.md` files and any
harness-specific instruction files. Respect scope: a nested rule may govern one
component without being repository-wide.

Resolve the kit root from an explicit path for this invocation, the
`AGENT_GUIDANCE_KIT_ROOT` environment setting, an ignored target-local locator,
or a validated adjacent `agent-guidance-kit` sibling, in that order. If none
works, ask. Do not search unrelated personal directories, fetch a replacement,
or embed a personal absolute path in tracked guidance.

### 2. Inventory facts without interpretation

Run:

```text
python3 <kit-root>/.agents/skills/bootstrap-project/scripts/inventory_project.py \
  --root <target-root> --format markdown
```

The inventory reports files, languages, build/test/CI markers, guidance files,
harness markers, and Git state. Verify important facts against the actual files.
Do not treat extension counts or filenames as architecture conclusions.

Read [harness integration guidance](references/harness-integration.md) and use
`harness-adaptation` when the target has multiple instruction systems, asks for
adapter setup, or the active harness's discovery behavior is unclear.

### 3. Select the smallest useful set

Read the frontmatter and body of every candidate skill before proposing it.
For each candidate, ask:

1. Does the target have a recurring or high-risk task this skill materially
   improves?
2. Is the workflow more specific than normal capable-model behavior?
3. Does an existing local skill already own the trigger?
4. Can a narrower project-specific skill serve better?
5. What behavior, evidence, or failure mode justifies its context cost?

Classify each reviewed skill:

- `ADD` — distinct useful workflow with no local owner.
- `ADAPT` — useful content belongs in an existing local owner rather than as a
  copied parallel skill.
- `KEEP_LOCAL` — target guidance is stronger or a same-name owner exists.
- `DEFER` — potentially useful, but a project decision or evidence is missing.
- `SKIP` — redundant, irrelevant, or generic advice with no demonstrated value.

The installer always adds `agent-guidance-maintenance` and recursively closes
declared `requires` dependencies. Declared `related` skills are suggestions,
not automatic additions. A relative skill link is allowed only for a required
dependency so a selective installation cannot create a broken link.

### 4. Reconcile the guidance hierarchy

Identify the target's canonical owners for:

- project invariants and task routing;
- small always-on operating norms;
- task-specific procedures;
- harness entrypoints and projections.

Before finalizing skill selection, perform a source-canonical drift check. The
kit's `.agents/AGENTS.md` and `.agents/OPERATING.md` are source-owned reference
guidance, while a target's copies remain target-owned and may contain stronger
project invariants. Run the recommender with `--json --diff` and treat every
`REVIEW`/`RECOMMEND` result as a plan item requiring an explicit disposition.
In particular, do not miss additive changes to `OPERATING.md` (such as a new
always-on quality baseline) merely because the installer receipt only tracks
skill directories. Preserve target-specific sections and propose an exact
`ADAPT`, `KEEP_LOCAL`, or `DEFER` decision; never silently replace the target
file.

Prefer adapting the target's current hierarchy. If it has none, propose a thin
root entrypoint, one canonical project rules/index file, one compact operating
file, and conditional skill directories. Do not create parallel canonical
sources.

For `AGENTS.md` and every harness adapter (`CLAUDE.md`, `GEMINI.md`,
`.github/copilot-instructions.md`, `.cursor/rules`, `.clinerules`,
`.claude/settings.json`, etc.):

1. Run `python3 <kit-root>/scripts/harness_recommendations.py --kit-root <kit-root> --target <target-root> --json --diff` to inventory bodies and get machine-readable findings plus paste-ready diffs.
2. Compare the target's `AGENTS.md` (root thin pointer) and `.agents/AGENTS.md` / `.agents/OPERATING.md` against the kit canonicals. A thick root `AGENTS.md` that duplicates `Product boundary` / `Skill index` is a `RECOMMEND` to thin; outdated `.agents/AGENTS.md` or `.agents/OPERATING.md` is a required `REVIEW`/adaptation item via `harness-adaptation` and `skill-authoring`, not an informational note.
3. For each harness file, classify as `KEEP_LOCAL` (strong target-specific policy), `ADAPT` (apply paste-ready thin-pointer diff), or `SKIP` (unused harness). Never auto-overwrite divergent harness content; use `harness-adaptation` + `skill-authoring` with approval gate.
4. Surface the table in the approval plan (Section 5) alongside skill decisions so the user sees `AGENTS.md` + harness upgrades together with skill adds.

Build a capability profile for the active harness rather than selecting from a
closed product list. Use native discovery when available, then a thin pointer,
then a narrow projection, and finally a manual invocation prompt. Unknown
harnesses are supported through the same profile and must be labeled
`BEST_EFFORT` until their discovery behavior is verified.

### 5. Present the approval plan

Before changing files, report:

| Item | Decision | Evidence | Destination/owner | Collision or risk |
| :--- | :--- | :--- | :--- | :--- |
| skill or guidance item | ADD / ADAPT / KEEP_LOCAL / DEFER / SKIP | target fact or repeated need | exact path | none or explicit issue |

Also list:

- every file to create or edit;
- exact copied skills;
- local guidance preserved unchanged;
- proposed text-level adaptations;
- harness projections, if any;
- every source-canonical guidance finding and its explicit disposition;
- validation commands;
- material exclusions and why.

Stop and obtain explicit approval for this exact scope.

### 6. Generate and apply the mechanical plan

After approval, create a plan in an ignored or temporary location:

```text
python3 <kit-root>/.agents/skills/bootstrap-project/scripts/install_skills.py \
  plan --kit-root <kit-root> --target <target-root> \
  --skill <approved-skill> --output <plan.json>
```

For a preview without writing a file, use `--diff` and/or `--check`:

```text
python3 <kit-root>/.agents/skills/bootstrap-project/scripts/install_skills.py \
  plan --kit-root <kit-root> --target <target-root> \
  --skill <approved-skill> --diff          # unified diff of skill + routing changes
python3 <kit-root>/.agents/skills/bootstrap-project/scripts/install_skills.py \
  plan --kit-root <kit-root> --target <target-root> \
  --skill <approved-skill> --check         # conflict-only; exit 1 if CONFLICT/ASK
python3 <kit-root>/.agents/skills/bootstrap-project/scripts/install_skills.py \
  plan --kit-root <kit-root> --target <target-root> \
  --skill <approved-skill> --diff --check  # diff plus conflict-only check
```

`--diff` also surfaces harness entrypoint recommendations (AGENTS.md,
CLAUDE.md, GEMINI.md, `.github/copilot-instructions.md`) when they exist
without referencing the canonical `.agents/AGENTS.md` — these are
informational and require `harness-adaptation` for paste-ready thin-pointer
updates. Review the plan's source digest, requested and automatically added skills,
required versus related dependencies, create/update/unchanged statuses,
destinations, managed AGENTS route, and conflicts. `CONFLICT` is a stop
condition; do not bypass it.

Apply only the unchanged approved plan:

```text
python3 <kit-root>/.agents/skills/bootstrap-project/scripts/install_skills.py \
  apply --kit-root <kit-root> --target <target-root> \
  --plan <plan.json> --approve
```

The helper revalidates source and destination state, stages complete skill
directories, creates missing destinations, atomically refreshes only content
whose current digest matches a prior receipt, maintains a digest-guarded route
block, and writes a content-hash receipt. Local divergence is a conflict and is
never overwritten.

If no higher-priority portable source already resolves the approved kit, the
first approved apply configures the ignored target-local source locator when the
target is a Git worktree. If the environment setting, existing locator, or
validated adjacent-sibling convention already resolves the same source, the
plan records that method and does not create redundant locator state. Verify
that future sessions can rediscover the source:

```text
python <target-root>/.agents/skills/agent-guidance-maintenance/scripts/resolve_source.py \
  resolve --target <target-root>
```

The resolver writes no tracked personal path. If automatic configuration is
unavailable, the plan stops until an existing adjacent-sibling fallback or
environment setting provides a portable future source.

### 7. Integrate target-local guidance

The installer creates or updates a managed AGENTS route block for every adopted
skill. That deterministic index is necessary but may not be sufficient semantic
integration. Apply only the approved additional edits needed to:

- route target tasks to the selected skills;
- record project-specific invariants derived from source/build/config truth;
- keep always-on rules compact;
- preserve existing precedence and nested scope;
- add thin harness pointers only where useful;
- record public source provenance without machine-specific paths.

Use `skill-authoring` for material skill edits. Keep copied generic skills
generic unless the approved plan explicitly makes them project-specific.

### 8. Verify and report

Run the target's relevant guidance validator, link checks, and project gates.
For a selective installation, run:

```text
python <target-root>/.agents/skills/agent-guidance-maintenance/scripts/validate_adoption.py \
  --target <target-root>
```

Re-read every created or edited instruction as a future agent would encounter
it. Confirm:

- no locally modified adopted file was overwritten or deleted;
- copied hashes match the receipt;
- all skill names, links, descriptions, and index entries align;
- no unfinished placeholders, personal paths, credentials, or private state
  entered tracked files;
- neighboring task prompts route predictably;
- all checks are reported as pass, fail, or not run with reason.

Report the approved decisions, receipt path, created/edited files, preserved
collisions, verification evidence, and deferred items. Do not claim a skill is
integrated merely because it was copied.
