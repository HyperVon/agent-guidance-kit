# Ecosystem recipes

Progressive-disclosure companion to `dependency-upgrade`. Load this when applying a
transitive remediation or choosing the deterministic update command for an
ecosystem. The security-first ordering, lockfile ownership, deterministic
regeneration requirement, and verification gates stay in `SKILL.md`.

## Transitive vulnerability remediation

When an advisory affects a transitive dependency and no parent package update is available:

- **npm:** Use the `"overrides"` field in `package.json` (e.g. `{"overrides": {"vulnerable-pkg": "^1.2.3"}}`).
- **pnpm:** Use the `pnpm.overrides` field in `package.json`.
- **yarn (v1 / v2+):** Use `"resolutions"` in `package.json`.
- **Cargo:** Use `[patch.crates-io]` or run `cargo update -p <package_name> --precise <version>`.
- **Go:** Use `go mod edit -replace` or specify the minimal required transitive version in `go.mod`.
- **Python:** Use `constraints.txt` or pinned transitive requirements in lockfile generators (e.g. `uv pip compile`, `poetry.lock`).
- **Maven:** Use `<dependencyManagement>` in the parent POM to pin the transitive dependency version without adding it as a direct dependency.
- **Gradle:** Use `constraints {}` in the `dependencies` block (e.g. `constraints { implementation("vulnerable-pkg:1.2.3") }`) or `resolutionStrategy.force` in `configurations.all`.

Never add an internal transitive library as a direct top-level runtime dependency unless the project explicitly imports it.

## Deterministic update commands

| Ecosystem | Targeted single-package update | Full gate check |
| :--- | :--- | :--- |
| **npm** | `npm install <pkg>@<ver> --package-lock-only` | `npm test && git diff package-lock.json` |
| **pnpm** | `pnpm update <pkg>@<ver>` | `pnpm test && git diff pnpm-lock.yaml` |
| **yarn** | `yarn up <pkg>@<ver>` | `yarn test && git diff yarn.lock` |
| **Python (uv)** | `uv lock --upgrade-package <pkg>` | `uv run pytest && git diff uv.lock` |
| **Python (poetry)** | `poetry update <pkg>` | `poetry check && poetry run pytest && git diff poetry.lock` |
| **Python (pip-tools)** | `pip-compile --upgrade-package <pkg> requirements.in` | `pytest && git diff requirements.txt` |
| **Cargo** | `cargo update -p <pkg> --precise <ver>` | `cargo test && git diff Cargo.lock` |
| **Go** | `go get <pkg>@<ver> && go mod tidy` | `go test ./... && git diff go.sum` |

These are examples, not an exhaustive list; detect the project's actual lockfile
tool and use its deterministic command. The full-gate check MUST always include
`git diff <lockfile>` and confirm only the targeted package tree changed.
