# Adoption prompt

Use this prompt in the target repository after making the Agent Guidance Kit
checkout available to the active coding harness. Replace only the two paths.

```text
Use the Agent Guidance Kit at /path/to/agent-guidance-kit to inspect the
repository at /path/to/project.

First identify the active harness and build the capability profile required by
the kit's harness-adaptation skill. Then follow bootstrap-project to inventory
the target, read all applicable target-local guidance, and propose the smallest
useful set of skills and integration changes.

Treat target-local guidance as authoritative. Always include the kit-owned
maintenance skill. Classify each other candidate as ADD, ADAPT, KEEP_LOCAL,
DEFER, or SKIP, with evidence and an exact destination or owner. Include every
proposed file creation or edit, dependency addition, collision, harness
projection, validation command, and material exclusion.

Do not use or install a local LLM, classifier, embeddings service, model router,
provider runtime, plugin, or worker supervisor. Do not read credentials or
runtime data, fetch remote guidance, execute imported scripts, overwrite local
guidance, or modify the target yet. Stop after the exact plan and wait for my
approval.
```

If the harness does not discover repository skills natively, explicitly direct
it to read these two entrypoints first:

```text
/path/to/agent-guidance-kit/.agents/skills/bootstrap-project/SKILL.md
/path/to/agent-guidance-kit/.agents/skills/harness-adaptation/SKILL.md
```

After approval, the harness should generate and review the deterministic
receipt-aware plan, apply it with `--approve`, configure the ignored source
locator when the plan calls for it, verify source rediscovery, run the adopted
target validator, make only separately approved integration edits, and report
the receipt and verification evidence.

## Updating an existing adoption

After the target has `agent-guidance-maintenance`, use this prompt:

```text
Use agent-guidance-maintenance to update Agent Guidance Kit to the latest
version. Resolve the existing kit checkout, verify that it is a clean `main`
worktree for the intended source, and refresh it from `origin/main` using only
fast-forward-safe Git operations. Show me the old and new source revisions, the
receipt-aware target refresh plan, conflicts, and verification commands. Do not
apply target changes until I approve the exact plan.
```

The maintenance skill refreshes the named local source only for this explicit
request. It stops on dirty, detached, non-`main`, divergent, or unexpected
source checkouts. A source refresh does not approve target changes, and a
refresh does not silently add optional related skills.

## Common maintenance prompts

Choose the closest prompt below. In every case, the agent should read the
target's local guidance first, preserve the target's canonical owners, show an
exact plan before mutation, and report verification evidence afterward.

### Audit an existing adoption without changing anything

```text
Use agent-guidance-maintenance to audit this repository's Agent Guidance Kit
adoption. Resolve the current source without fetching or changing it, inspect
receipts, adopted skill digests, managed AGENTS routing, dependency declarations,
and source revision, then report any drift, conflicts, missing content, broken
links, or stale routing. This is read-only; do not modify anything.
```

### Refresh adopted content from the currently resolved source

```text
Use agent-guidance-maintenance to refresh the Agent Guidance Kit content this
repository has already adopted. Do not update the source checkout. Compare the
current source with receipt-owned target content, show the exact update plan,
conflicts, digests, routing changes, and verification commands, and do not
modify anything until I approve the exact plan.
```

### Add a specific skill

Replace `<skill-name>` with a catalog skill such as `security-review`,
`documentation-review`, or `quality-hardening`.

```text
Use agent-guidance-maintenance to add the Agent Guidance Kit skill
`<skill-name>` to this repository. Read the target guidance and current source,
explain why the skill is useful here, include only its declared required
dependencies, leave optional related skills unselected, show the complete
receipt-aware plan and validation commands, and wait for my approval before
applying it.
```

### Review the current catalog for useful additions

```text
Use agent-guidance-maintenance and the current Agent Guidance Kit source to
review whether any newly available skills would materially help this repository.
Compare the catalog with existing project guidance and recurring tasks. Classify
each candidate as ADD, ADAPT, KEEP_LOCAL, DEFER, or SKIP with evidence, owner,
context cost, conflicts, and verification criteria. This is a recommendation
only; do not install or edit anything.
```

### Adapt the canonical guidance to the active harness

```text
Use harness-adaptation to inspect the active coding harness and this
repository's current instruction discovery. Preserve the canonical Agent
Guidance Kit files and target-local authority, then propose the thinnest useful
native pointer or projection. Label unsupported behavior BEST_EFFORT, include
reload and verification steps, and do not modify anything until I approve the
exact adapter plan.
```

### Propose target-specific integration after installing skills

```text
Use bootstrap-project to review the installed Agent Guidance Kit skills against
this repository's build, tests, architecture, and existing guidance. Propose
only the smallest target-specific routing, invariant, or harness-entrypoint
edits that are supported by repository evidence. Preserve stronger local rules,
list every file and owner, and wait for approval before editing.
```

### Verify an adoption after approval

```text
Use agent-guidance-maintenance to verify the current Agent Guidance Kit
installation after its approved plan was applied. Check the receipt, source
revision, skill content digests, required-dependency closure, relative links,
managed AGENTS index, source rediscovery, and the target's relevant project
gates. Report every pass, failure, skip, and conflict; do not make repair edits
automatically.
```

### Investigate a local-modification conflict

```text
Use agent-guidance-maintenance to explain the Agent Guidance Kit conflict in
this repository. Identify the locally modified adopted file or managed route,
compare it with the receipt and current source, and propose safe choices such as
preserve-local, manually reconcile, or create a new approved plan. Do not
overwrite, delete, or merge the local content automatically.
```

These prompts intentionally do not describe uninstalling adopted skills. The
kit currently provides safe adoption, audit, addition, refresh, update, and
verification workflows; removal should be handled as a separately designed,
explicit target-local change rather than an implicit maintenance operation.
