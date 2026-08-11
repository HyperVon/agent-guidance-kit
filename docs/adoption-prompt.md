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
