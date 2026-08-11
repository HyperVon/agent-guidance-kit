# Agent Guidance Kit

Agent Guidance Kit is a small, skills-first library for improving an existing
software repository's project-local agent guidance.

The active coding agent does the judgment. It inspects the target repository,
understands the local rules, chooses the smallest useful set of skills, and
proposes how to integrate them. Deterministic scripts only collect facts,
preview safe copy operations, apply an approved create-only plan, and validate
the result.

> Status: pre-v1 local development. The public API and catalog may still change.

## What this project is

- A curated library of reusable software-engineering skills.
- A `bootstrap-project` front door for repository-specific selection and
  integration.
- A compact hierarchy: thin harness entrypoints, canonical project rules,
  small always-on norms, and conditional deep skills.
- A capability-based adapter workflow for current and future agent harnesses,
  without making compatibility depend on a closed product allowlist.
- A safe, review-first way to copy selected skills without overwriting local
  files.

## What this project is not

- An embedded or local LLM, classifier, embeddings service, or semantic engine.
- A model router, provider abstraction, quota manager, agent runtime, or worker
  supervisor.
- A framework that replaces a target repository's existing instructions.
- A network installer, marketplace, pack registry, or automatic updater.

## Quick start

The cleanest workflow is to make this checkout visible to a capable coding
agent and ask it to read:

```text
.agents/skills/bootstrap-project/SKILL.md
```

Example request:

```text
Use bootstrap-project from /path/to/agent-guidance-kit to inspect this
repository. Propose the smallest useful set of skills and guidance changes.
Do not modify anything until I approve the exact plan.
```

For a complete copy-paste version that also profiles the current harness, use
the [adoption prompt](docs/adoption-prompt.md).

To copy only the bootstrap and harness-adaptation skills into a target
repository, create a plan first:

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

The installer creates missing skill directories only. It refuses the entire
apply when any destination differs, and it never merges or overwrites guidance.
Common interpreter caches and editor/OS debris are excluded from the content
manifest and copied output.

Then ask the target project's agent to use the copied bootstrap skill and the
full kit checkout to propose further adoption. The bootstrap workflow preserves
existing local guidance and requires approval before integration edits.

## Included skills

The initial catalog contains:

- `bootstrap-project`
- `ai-slop-detector`
- `architecture-review`
- `code-review`
- `documentation-review`
- `harness-adaptation`
- `quality-hardening`
- `reduce-code-size`
- `parallel-multi-agent`
- `skill-authoring`
- `skill-reviewer`
- `rules-and-skills-audit`
- `skill-optimizer`

These are deliberately broad enough to reuse and narrow enough to trigger
predictably. Technology, domain, deployment, and product-specific skills belong
in the consuming repository.

## Harness compatibility

The canonical `AGENTS.md` hierarchy and `.agents/skills/` catalog are directly
discoverable by many current harnesses. Thin checked-in adapters cover Claude
Code, Gemini CLI, and GitHub Copilot without duplicating the canonical skill
bodies. Harnesses with incomplete public discovery contracts use the manual
entrypoint from `harness-adaptation` until their behavior is verified.

Compatibility is determined by capability at adoption time, not by a closed
list in the installer. See the dated [compatibility evidence and support
levels](docs/harness-compatibility.md).

## Development

Requirements: Python 3.11 or newer and Node.js 22 or newer with npm. `make` is
optional.

Cross-platform setup:

```text
python scripts/setup_dev.py
```

Run all checks on macOS/Linux:

```text
.venv/bin/python scripts/check.py
```

Run all checks on Windows PowerShell or Command Prompt:

```text
.venv\Scripts\python.exe scripts\check.py
```

On macOS/Linux, the equivalent convenience commands are:

```text
make setup
make check
```

The adoption and inventory tools use only the Python standard library. Project
validation uses PyYAML so skill frontmatter and metadata are checked as real
YAML. Ruff checks and formats the Python code, and markdownlint-cli2 validates
Markdown. `make setup` installs these into ignored project-local environments;
`make check` itself contacts no network service.

### What setup installs

`make setup` creates `.venv/` and `node_modules/` inside this checkout and
installs only the pinned development dependencies declared in
`requirements-dev.txt` and `package-lock.json`:

- PyYAML — parses and validates `SKILL.md` frontmatter and `agents/openai.yaml`.
- Ruff — lints Python and verifies its formatting before commit or push.
- markdownlint-cli2 — lints every Markdown and MDC file before commit or push.

Python packages are installed in `.venv/`; Node packages are installed in
`node_modules/` with dependency lifecycle scripts disabled. Setup does not
modify the system Python or Node.js, install an LLM, download a model, add a
browser or agent plugin, authenticate a provider, or install dependencies into
a target repository. The bootstrap workflow must propose any target-project
tooling change separately and obtain the user's approval.

The functional scripts use `pathlib`, argument lists rather than shell command
strings, and platform-neutral file operations. The checked-in CI workflow is
configured to run the same check suite on Windows, Linux, and macOS once the
project is hosted. Pre-v1 local acceptance is currently verified on macOS;
other platforms remain intended and CI-configured, not yet confirmed.

See [the design](docs/design.md), [contributing guidance](CONTRIBUTING.md), and
[source provenance](docs/provenance.md) for the project boundaries. The
[roadmap](docs/roadmap.md) separates future skill-library research from an
optional sibling routing runtime.

## License

Apache License 2.0. See [LICENSE](LICENSE).

## Public-data policy

Tracked files must not contain credentials, account data, private repository
coordinates, local runtime state, personal filesystem paths, machine names, or
secret-bearing examples. Use placeholders such as `/path/to/project` and
`example.invalid`.
