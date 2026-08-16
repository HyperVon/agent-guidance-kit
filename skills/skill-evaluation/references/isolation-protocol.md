# Evaluation isolation protocol

Progressive-disclosure companion to `skill-evaluation`. Load this only when
setting up or troubleshooting worker isolation for a clean-context evaluation.
The safety invariants that decide whether a run is valid stay in `SKILL.md`;
this file holds the filesystem/sandbox procedure and troubleshooting.

## Filesystem and harness containment

- For Codex CLI, use a task-matched sandbox. Report-only tasks may use an
  isolated write-enabled root so the parent can verify that no edits occurred;
  implementation or test-hardening tasks require write access. Use read-only
  only when the task genuinely requires no writes, and record that limitation
  when it makes a no-edit assertion uninformative.
- Capture stdout, stderr, and session JSONL in a parent-only directory outside
  every worker root; never redirect them into a worker workspace, because the
  worker can inspect its own trace.
- A neutral name is not filesystem isolation: when the harness allows parent
  traversal, the worker must not be able to enumerate sibling roots, the
  catalog checkout, other worktrees, memory, or parent-only logs.
- Use an OS-level jail, container, or equivalent profile that denies those paths
  and allows only the worker root plus the runtime files genuinely required to
  start the harness.

## Worker environment separation

- Each worker runs in its own root containing only the declared fixtures; do not
  place workers in a shared temporary parent, repository collection, or workspace
  whose siblings the agent can inspect.
- Restrict file, tool, and network access to the case when the harness supports
  it; otherwise state the limitation and exclude any run contaminated by
  unrelated discovery.
- Set the worker's actual working directory, or have the runner verify `pwd` and
  an immediate file manifest before the task begins. A path mentioned in a prompt
  is not isolation.

## Boundary probe

Run a parent-side boundary probe before scoring:

```text
pwd               # worker's actual working directory
local manifest    # files the worker can see
parent traversal  # attempt to reach sibling roots / catalog checkout / parent-only logs
catalog-path access # attempt to reach the target skill or its references
```

Any unexpected success contaminates the condition and invalidates the run.

### Codex CLI sandbox note

For Codex CLI on macOS, the inner sandbox may block a nonstandard contained
root. After verifying an outer `sandbox-exec`/seatbelt profile, the runner may
use `--dangerously-bypass-approvals-and-sandbox` so that the outer profile remains
authoritative; never use that flag without verified outer containment, and record
the profile and denied-path probes.

## Isolation-failure troubleshooting

| Symptom | Meaning | Action |
| :--- | :--- | :--- |
| Worker starts in the catalog repository or can see sibling evaluation metadata | Condition is contaminated | Discard the run |
| Baseline worker receives the target skill's name, path, description, catalog entry, injection label, or skill-list metadata through system prompt, banner, tool manifest, or other automatic projection | Condition is contaminated even if skill text is not loaded | Mark contaminated, do not score |
| Discovered `AGENTS.md` guidance carries the injection | Baseline may leak the condition | Use separate neutral variants; the guided variant may name a neutral guidance path, the baseline must not mention that path or use an `if-exists` check |
| Harness cannot create and verify independent contexts (including absence of target-skill identity in baseline-visible system metadata) | No valid comparison possible | Leave the matrix untested, report the limitation |
| An interrupted pair, partial case, or model-switch run | Mixed with completed result | Exclude rather than silently combine |
