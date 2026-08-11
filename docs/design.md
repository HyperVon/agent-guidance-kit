# Design

## Goal

Upgrade an arbitrary software repository with the smallest useful set of proven
agent skills and operating guidance while preserving that repository's local
authority.

## Architecture

```text
active harness LLM
  -> identify its instruction and skill capabilities
  -> inspect target repository and existing guidance
  -> read reusable skill catalog
  -> propose selection and integration plan
  -> stop for approval
  -> copy approved skills with deterministic create-only helper
  -> adapt target-local routing and invariants
  -> validate and report evidence
```

The LLM owns interpretation and reconciliation because those tasks depend on
project meaning. Scripts own repeatable mechanical checks because those tasks
benefit from determinism.

## Guidance hierarchy

```text
root AGENTS.md and harness entrypoints
  -> thin pointers

.agents/AGENTS.md
  -> project invariants and task-to-skill routing

.agents/OPERATING.md
  -> small always-on behavior

.agents/skills/*/SKILL.md
  -> deep task-triggered procedures
```

This hierarchy is a pattern, not a required filesystem rewrite. A consuming
project may have another canonical guidance layout. Bootstrap must preserve and
integrate with that layout rather than install a competing source of truth.

## Harness adaptation

Harness compatibility is capability-based. Bootstrap asks the active harness
how it discovers repository instructions and skills, how precedence and nested
scope work, whether it can follow canonical-file pointers, what reload behavior
is required, and how discovery can be verified. It then chooses the thinnest
working projection.

Product-specific profiles document known behavior and test evidence, but they
are not a runtime allowlist. An unknown future harness can use native discovery,
a thin instruction pointer, a narrow projection, or a manual entrypoint without
requiring a new release of the kit. The repository keeps one canonical owner
for each rule or skill regardless of the adapter used.

## Safety model

- External and reusable guidance is input to review, not automatically trusted
  policy.
- Inventory and planning are read-only.
- Adoption is approval-gated.
- Mechanical copy is create-only and preflights every conflict before writing.
- Existing target guidance remains authoritative.
- Scripts do not execute imported content or access networks, providers,
  credentials, databases, logs, or runtime state.

## Deliberate exclusions

V1 does not include an LLM, embeddings, provider selection, model routing,
worker spawning, process supervision, automatic updates, remote pack loading,
marketplace behavior, or a managed-guidance state machine. Those capabilities
must earn a separate boundary through demonstrated use.
