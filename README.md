# Agent Guidance Kit

[![Check](https://github.com/HyperVon/agent-guidance-kit/actions/workflows/check.yml/badge.svg)](https://github.com/HyperVon/agent-guidance-kit/actions/workflows/check.yml)
[![Validated skills: 24](https://img.shields.io/badge/Validated%20skills-24-brightgreen)](.agents/AGENTS.md) [![Evaluated: 22/24](https://img.shields.io/badge/Evaluated-22%2F24-blue)](docs/evaluations/validation-matrix.md) [![Harness: DOCUMENTED (muse)](https://img.shields.io/badge/Harness-DOCUMENTED%20(muse)-blue)](docs/harness-compatibility.md)

Agent Guidance Kit helps a coding agent add curated, project-local guidance to
an existing software repository without replacing that repository's own rules.

The agent inspects the target project, proposes the smallest relevant set of
skills, and waits for approval. A deterministic installer then adds the kit's
maintenance entrypoint, closes required dependencies, updates managed routing,
and installs the approved skills without overwriting local divergence.

> Status: v1.1.0 (2026-08-12) — 24 catalog skills, 22/24 evaluated, harness DOCUMENTED (muse). The catalog and integration workflow may evolve
> in backward-compatible releases.

## Why use it

- Start a project with reusable review, quality, documentation, architecture,
  and skill-authoring workflows.
- Keep one canonical set of project rules while adapting to the coding harness
  currently in use.
- Review every proposed addition before changing the target repository.

## Quick start

Clone the repository, or make an existing checkout available to your coding
agent:

```text
git clone https://github.com/HyperVon/agent-guidance-kit.git
```

Then ask the agent to read:

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

### Update an existing adoption

After the target has the receipt-managed `agent-guidance-maintenance` skill,
ask its agent to update the source checkout and prepare a refresh plan:

```text
Use agent-guidance-maintenance to update Agent Guidance Kit to the latest
version. Resolve the existing kit checkout, verify that it is a clean `main`
worktree for the intended source, and refresh it from `origin/main` using only
fast-forward-safe Git operations. Show me the old and new source revisions, the
receipt-aware target refresh plan, conflicts, and verification commands. Do not
apply target changes until I approve the exact plan.
```

The source checkout is refreshed only for this explicit request. Dirty,
detached, non-`main`, divergent, or unexpected-source checkouts stop for user
direction. Refreshing the source does not itself approve changes in the target;
the normal plan and approval gate still applies. To add newly available skills,
ask the agent to review candidates separately; a refresh updates adopted
receipt-owned content but does not silently add optional related skills.

See the [prompt cookbook](docs/adoption-prompt.md#common-maintenance-prompts)
for audit, refresh, skill-addition, harness-adaptation, verification, and
conflict-investigation examples.

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
the source checkout path. Kit-side evaluation material under `evals/` is not
copied into consuming repositories.

## Included skills

The catalog covers:

- Adoption and compatibility: `agent-guidance-maintenance`, `bootstrap-project`,
  `harness-adaptation`, `catalog-discovery`
- Review and quality: `ai-slop-detector`, `architecture-review`, `code-review`,
  `documentation-review`, `quality-hardening`, `security-review`,
  `systematic-debugging`, `adversarial-pr-review`, `frontend-quality-review`,
  `threat-modeling`
- Project and skill maintenance: `parallel-multi-agent`, `reduce-code-size`,
  `rules-and-skills-audit`, `skill-authoring`, `skill-evaluation`,
  `skill-optimizer`, `skill-reviewer`, `git-github-workflow`,
  `dependency-upgrade`, `upstream-contribution`

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
- Agent Skills reference validation via the `agentskills` command from the
  pinned `skills-ref` package
- markdownlint-cli2 for Markdown and MDC linting

Node dependency lifecycle scripts are disabled during setup. The complete check
runs without network access and is required before commit or push. CI runs the
same check on Windows, Ubuntu, and macOS with Python 3.11 and 3.14.

## Project documentation

- [Design and safety model](docs/design.md)
- [Contributing](CONTRIBUTING.md)
- [Source provenance](docs/provenance.md)
- [Validation matrix](docs/evaluations/validation-matrix.md) — where evaluations have been tested and confirmed better than baseline ([human-readable muse-spark run](docs/evaluations/results/2026-08-11-muse-spark-1.2-contributor-muse-code.md), [machine-readable JSON](docs/evaluations/results/2026-08-11-muse-spark-1.2-contributor-muse-code.json))
- [Catalog expansion evaluation](docs/evaluations/2026-08-10-catalog-expansion.md)
- [Systematic debugging fixture evaluation](docs/evaluations/2026-08-11-systematic-debugging-fixture.md)
- [External skill intake evaluation](docs/evaluations/2026-08-10-external-skill-intake.md)
- [Roadmap](docs/roadmap.md)
- [Security policy](SECURITY.md)

## License

Apache License 2.0. See [LICENSE](LICENSE).
