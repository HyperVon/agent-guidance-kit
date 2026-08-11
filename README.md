# Agent Guidance Kit

Agent Guidance Kit helps a coding agent add proven, project-local guidance to
an existing software repository without replacing that repository's own rules.

The agent inspects the target project, proposes the smallest relevant set of
skills, and waits for approval. A deterministic installer then adds the kit's
maintenance entrypoint, closes required dependencies, updates managed routing,
and installs the approved skills without overwriting local divergence.

> Status: early release. The catalog and integration workflow may change before
> the first versioned release.

## Why use it

- Start a project with reusable review, quality, documentation, architecture,
  and skill-authoring workflows.
- Keep one canonical set of project rules while adapting to the coding harness
  currently in use.
- Review every proposed addition before changing the target repository.

## Quick start

Make this checkout available to your coding agent and ask it to read:

```text
.agents/skills/bootstrap-project/SKILL.md
```

Example request:

```text
Use bootstrap-project from /path/to/agent-guidance-kit to inspect this
repository. Propose the smallest useful set of skills and guidance changes.
Do not modify anything until I approve the exact plan.
```

The [adoption prompt](docs/adoption-prompt.md) provides a longer copy-paste
request that also profiles the current harness.

### Optional deterministic installer

The agent can prepare a receipt-aware installation plan for selected skills:

```text
python3 /path/to/agent-guidance-kit/.agents/skills/bootstrap-project/scripts/install_skills.py \
  plan --kit-root /path/to/agent-guidance-kit \
  --target /path/to/project \
  --skill bootstrap-project --skill harness-adaptation \
  --output /path/to/plan.json
```

After reviewing the plan and its ID, apply that unchanged plan explicitly:

```text
python3 /path/to/agent-guidance-kit/.agents/skills/bootstrap-project/scripts/install_skills.py \
  apply --kit-root /path/to/agent-guidance-kit \
  --target /path/to/project \
  --plan /path/to/plan.json --approve
```

The installer always includes `agent-guidance-maintenance`, adds declared
required dependencies, and leaves optional related skills unselected. It
creates missing skills and may refresh an adopted skill only when its current
content still matches a prior receipt. Local modifications or routing conflicts
stop the entire operation. The approved plan also creates or updates a managed
AGENTS routing block so future agents can discover maintenance without knowing
the source checkout path.

## Included skills

The initial catalog covers:

- Adoption and compatibility: `agent-guidance-maintenance`, `bootstrap-project`,
  `harness-adaptation`
- Review and quality: `ai-slop-detector`, `architecture-review`, `code-review`,
  `documentation-review`, `quality-hardening`, `security-review`,
  `systematic-debugging`
- Project and skill maintenance: `parallel-multi-agent`, `reduce-code-size`,
  `rules-and-skills-audit`, `skill-authoring`, `skill-evaluation`,
  `skill-optimizer`, `skill-reviewer`

Technology, product, and domain-specific guidance remains in the consuming
repository.

## Harness compatibility

The kit keeps its canonical guidance in `AGENTS.md`, `.agents/AGENTS.md`,
`.agents/OPERATING.md`, and `.agents/skills/`. Thin checked-in entrypoints cover
Claude Code, Gemini CLI, and GitHub Copilot. Other harnesses use native
discovery or the manual adaptation workflow according to their capabilities.

See the dated [harness compatibility evidence](docs/harness-compatibility.md)
for current support levels and reload guidance.

## Development

Requirements: Python 3.11 or newer and Node.js 22 or newer with npm. `make` is
optional.

Set up the project on Windows, macOS, or Linux:

```text
python scripts/setup_dev.py
```

Run the complete check on macOS or Linux:

```text
.venv/bin/python scripts/check.py
```

Run it on Windows:

```text
.venv\Scripts\python.exe scripts\check.py
```

Setup creates ignored `.venv/` and `node_modules/` directories and installs the
pinned development tools declared by the repository:

- PyYAML for skill and metadata validation
- Ruff for Python linting and formatting checks
- markdownlint-cli2 for Markdown and MDC linting

Node dependency lifecycle scripts are disabled during setup. The complete check
runs without network access and is required before commit or push. CI runs the
same check on Windows, Ubuntu, and macOS with Python 3.11 and 3.14.

## Project documentation

- [Design and safety model](docs/design.md)
- [Contributing](CONTRIBUTING.md)
- [Source provenance](docs/provenance.md)
- [Catalog expansion evaluation](docs/evaluations/2026-08-10-catalog-expansion.md)
- [External skill intake evaluation](docs/evaluations/2026-08-10-external-skill-intake.md)
- [Roadmap](docs/roadmap.md)
- [Security policy](SECURITY.md)

## License

Apache License 2.0. See [LICENSE](LICENSE).
