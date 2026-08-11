---
name: bootstrap-project
description: "Inspect an existing software repository, compare its local agent guidance with this reusable skill library, and propose the smallest useful approval-gated integration. Use when starting agent guidance in a project, adopting this kit, selecting reusable skills, reconciling AGENTS or harness instructions, or reviewing whether a project would benefit from additional project-local skills. Report and plan by default; modify the target only after explicit approval of the exact adoption plan."
---

# Bootstrap a Project

Use the active coding harness and its current LLM to understand the target
project and choose guidance. Use bundled scripts only for mechanical facts,
hashes, create-only copy, and validation.

## Contract

- **Inputs:** target repository root, this kit's root, the user's objective, and
  all applicable target-local guidance.
- **Default output:** repository facts, guidance inventory, proposed selection,
  conflicts, integration edits, verification plan, and explicit approval gate.
- **Default side effects:** none. Inventory and proposal work are read-only.
- **Apply side effects:** copy only approved missing skill directories, then
  make separately approved target-local guidance edits.
- **Stop conditions:** stop before mutation; stop on an unresolved collision,
  symlink, source drift, target drift, unclear canonical owner, secret exposure,
  or a material choice the user has not made.

Do not install every skill. Do not add generic advice the base model already
handles well. Do not replace stronger project-local guidance.

## Hard boundaries

- Do not use a local LLM, embedded classifier, embeddings, or a separate
  semantic service. The active harness model performs selection and
  reconciliation.
- Do not fetch remote guidance, execute imported scripts, install packages,
  authenticate providers, start services, or inspect credentials/runtime data.
- Do not add provider routing, quota policy, worker supervision, or model
  catalogs to the target.
- Do not overwrite, delete, rename, or silently merge existing target guidance.
- Treat copied skills as target-local policy only after their content and
  integration have been reviewed and approved.

## Workflow

### 1. Establish roots and authority

Resolve the target repository and kit roots. Read the target's nested guidance
before interpreting it, including applicable `AGENTS.md` files and any
harness-specific instruction files. Respect scope: a nested rule may govern one
component without being repository-wide.

If the kit root is unavailable, ask for it. Do not search unrelated personal
directories or fetch a replacement from the network.

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

### 4. Reconcile the guidance hierarchy

Identify the target's canonical owners for:

- project invariants and task routing;
- small always-on operating norms;
- task-specific procedures;
- harness entrypoints and projections.

Prefer adapting the target's current hierarchy. If it has none, propose a thin
root entrypoint, one canonical project rules/index file, one compact operating
file, and conditional skill directories. Do not create parallel canonical
sources.

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

Review the plan's source digest, selected skills, statuses, destinations, and
conflicts. `CONFLICT` is a stop condition; do not bypass it.

Apply only the unchanged approved plan:

```text
python3 <kit-root>/.agents/skills/bootstrap-project/scripts/install_skills.py \
  apply --kit-root <kit-root> --target <target-root> \
  --plan <plan.json> --approve
```

The helper revalidates source and destination state, stages complete skill
directories, creates only missing destinations, and writes a content-hash
receipt. It never merges or overwrites.

### 7. Integrate target-local guidance

Copying files is not integration. Apply only the approved edits needed to:

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
Re-read every created or edited instruction as a future agent would encounter
it. Confirm:

- no local file was overwritten or deleted;
- copied hashes match the receipt;
- all skill names, links, descriptions, and index entries align;
- no unfinished placeholders, personal paths, credentials, or private state
  entered tracked files;
- neighboring task prompts route predictably;
- all checks are reported as pass, fail, or not run with reason.

Report the approved decisions, receipt path, created/edited files, preserved
collisions, verification evidence, and deferred items. Do not claim a skill is
integrated merely because it was copied.
