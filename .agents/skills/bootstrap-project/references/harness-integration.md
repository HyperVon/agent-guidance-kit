# Harness integration

Read this reference only when a target repository uses multiple agent harnesses
or asks for harness-specific entrypoints. Use `harness-adaptation` for the full
capability-profile workflow. The current dated evidence snapshot is in
[harness compatibility](../../../../docs/harness-compatibility.md).

## Discovery

Inventory repository-local instruction and skill markers without assuming that
a filename proves support. Ask the active harness to identify its capabilities,
then verify behavior from installed help or current primary documentation when
the distinction affects the integration.

Capture:

- automatically discovered instruction paths and nested scope;
- instruction precedence and composition/import behavior;
- native project-local skill paths and accepted `SKILL.md` fields;
- explicit skill invocation and discovery diagnostics;
- reload, restart, trust, or new-task requirements;
- one harmless verification action.

Known product profiles are examples, not a closed list. For an unknown or
changed harness, apply the capability contract rather than refusing support or
guessing a brand-specific file.

## Canonical ownership

Prefer one canonical owner for each kind of guidance:

| Concern | Canonical owner | Harness files |
| :--- | :--- | :--- |
| Project invariants and task routing | project rules/index | thin pointers or narrow required reminders |
| Always-on operating behavior | compact operating file | thin projections when a harness cannot follow the canonical file |
| Deep task procedure | one focused skill | native discovery path, registration metadata, or invocation alias |
| Provider/model/worker policy | active harness or separate runtime | never duplicated into portable skills |

Harness projections may repeat a short dangerous boundary when that harness
would otherwise miss it. Name the canonical source and keep repeated text
aligned.

## Model and worker behavior

- Use the active harness's native model and worker controls.
- Treat a role, profile, or agent name as a responsibility label, not proof of
  the underlying model or provider.
- Report an exact route only when the harness exposes it.
- Delegate only with user authority, disjoint ownership, bounded context, a
  sensitive-path denylist, an iteration/stop limit, and parent-owned
  integration.
- Keep provider credentials, catalogs, prices, quotas, cooldown state, and
  fallback implementation outside this guidance kit.

## Avoid

- Duplicating full canonical rules or physical skill bodies for every harness.
- Installing every adapter preemptively.
- Copying source-project commands or agent definitions into an unrelated
  repository.
- Reading `.env`, credentials, databases, logs, kubeconfigs, account data, or
  other runtime state to decide which guidance applies.
- Claiming a harness loaded guidance based only on file presence.
