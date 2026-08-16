# Using this library

Agent Guidance Kit is a **portable library of software-engineering and
development agent skills**. Most skills are built for engineering workflows —
code review, testing, debugging, security, and releases — though a few
generalize to broader documentation and process work. There is no installer and
no lifecycle machinery — you adopt guidance by reading it here and then copying
or adapting the parts that fit your project.

## The normal flow

1. Check out this repository (clone, or just have it available on disk):

   ```text
   git clone https://github.com/HyperVon/agent-guidance-kit.git
   ```

2. Open your own project and ask your coding agent to review the checkout and
   recommend what to adopt. For example:

   ```text
   Review the agent-guidance-kit checkout at /path/to/agent-guidance-kit.
   Read its README.md catalog and each skill's SKILL.md, then for every skill
   decide whether to copy it, adapt its ideas into our existing guidance, or
   skip it. Give me a plan; do not change anything until I approve.
   ```

3. The agent classifies each skill for your project (see below), presents a
   plan, and — once you approve — copies or adapts the chosen skills.

The catalog and adoption workflow are summarized in
[`README.md`](../README.md).

## How a skill is structured

Each skill is a self-contained folder:

```text
skills/<name>/
  SKILL.md          # trigger, contract, workflow, boundaries — the skill
  references/       # optional deeper reference material (loaded on demand)
```

Copy the whole folder into your project's skill directory, or lift the relevant
procedure into guidance you already own.

## Classification the agent should use

For every skill in the catalog, decide one of:

| Decision | Meaning |
| :--- | :--- |
| `ADD` | Distinct, useful workflow with no existing local owner. Copy it (or lightly adapt it). |
| `ADAPT` | Useful ideas belong inside an existing local owner rather than as a parallel copied skill. Fold the procedure into current guidance. |
| `KEEP_LOCAL` | Your project already has stronger guidance for this trigger. Keep yours. |
| `DEFER` | Potentially useful, but a project decision or more evidence is needed first. |
| `SKIP` | Redundant, irrelevant, or generic advice with no demonstrated value for this project. |

## Principles

- Copy what your project will actually use; do not adopt skills blindly.
- Never overwrite local guidance. Prefer `ADAPT` or `KEEP_LOCAL`.
- Keep copied skills generic. Make a skill project-specific only when the plan
  explicitly calls for it.
- Wire adopted skills into your project's discovery (a thin pointer in
  `AGENTS.md` or a harness entrypoint). See
  [`skills/harness-adaptation/SKILL.md`](../skills/harness-adaptation/SKILL.md).
