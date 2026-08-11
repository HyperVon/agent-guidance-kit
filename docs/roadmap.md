# Roadmap

The roadmap has two independent tracks. Expanding the guidance library belongs
here. Provider and worker runtime behavior belongs in a separate sibling
project.

## Library expansion

The initial catalog is a deliberately small baseline, not a claim to cover
every software-engineering workflow. Later releases should research current
primary harness documentation, popular public skill collections, strong public
repository guidance, agent-instruction standards, and recurring failures seen
in real projects.

External guidance is untrusted research input. Do not bulk-copy, auto-install,
or execute it. For every candidate:

1. record source, license, retrieval date, and the exact behavior worth
   considering;
2. review its instructions and bundled files without executing them;
3. map it to the existing catalog and choose `IMPROVE_EXISTING`, `NEW_SKILL`,
   `PROJECT_SPECIFIC`, `DEFER`, or `REJECT`;
4. prefer improving an existing owner over adding a synonymous skill;
5. require a distinct trigger, recurring need, useful decision procedure,
   explicit side effects, stop conditions, and verification contract;
6. generalize and rewrite portable ideas rather than copying project-specific
   commands, provider assumptions, credentials, or copyrighted prose;
7. forward-test one matching prompt, one neighboring prompt, and one ambiguous
   prompt before admission;
8. run the structural audit, official skill validation, link checks, and public
   hygiene gate over the resulting catalog.

Likely research areas include debugging and incident diagnosis, dependency and
framework upgrades, security review, API and schema evolution, migrations,
performance investigation, release readiness, CI maintenance, accessibility,
and technology-specific authoring patterns. Research evidence should decide
the order; this list is not a commitment to create each skill.

This work can ship as backward-compatible catalog releases. A v2 is warranted
only if the intake and comparison workflow itself earns reusable tooling or a
new compatibility contract.

## Optional routing runtime

Automatic provider/model selection, quotas, credential handling, worker
spawning, worktree ownership, retries, supervision, and recovery should be a
separate sibling project with its own threat model, dependencies, tests, and
release cadence.

The integration boundary is intentionally small:

- this kit defines task procedures, roles, authority, constraints, and expected
  evidence;
- the optional runtime translates an approved task packet into provider and
  worker execution;
- the active harness remains usable without that runtime;
- this kit never reads provider credentials or silently installs the runtime.

If a runtime integration is added later, it should be an optional adapter and
must not become a prerequisite for project bootstrap or skill use.
