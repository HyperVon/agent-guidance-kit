---
name: dependency-upgrade
description: >-
  Upgrade pinned dependencies safely — inventory across manifests and lockfiles,
  address security alerts first, group bumps by risk, and verify with full gates
  after each group. Use when updating dependencies, bumping versions,
  refreshing lockfiles, or addressing security alerts.
---

# Dependency Upgrade

Upgrade pinned dependencies in risk-ordered, reviewable groups. Never use
floating `latest` tags. Verify with the full gates after each group.

## Authority and scope

This skill owns the repeatable workflow for moving pinned manifests and
lockfiles forward. It does not own architecture, feature work, or deployment.
Work only in the requested scope and preserve behavior, wire formats, and
distinct tests.

## Step 1 — Security alerts first

Triage **all** open security alerts, then prioritize. Where GitHub Dependabot
alerts are available, use them as the authoritative source; otherwise use the
target repository or ecosystem's authoritative vulnerability or advisory source
(for example the package registry's advisory database or the language's
security tooling). A useful GitHub example:

```bash
gh api repos/{owner}/{repo}/dependabot/alerts --jq \
  '.[] | select(.state == "open") | [.number, .security_advisory.severity, .dependency.package.name, .dependency.manifest_path, (.security_vulnerability.vulnerable_version_range // "?")] | @tsv'
```

- Triage all open alerts; prioritize `critical` and `high` severity and
  document blockers or unfixable alerts with owner and next step rather than
  ignoring medium or low findings without triage.
- An alert identifies a vulnerable range, not the fixed version — confirm a supported remediation version or dependency path exists and can be expressed through the owning manifest or lockfile before changing dependency state.
- Never delete a security pin to make the build pass.

### Transitive vulnerability remediation

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

## Step 2 — Inventory

Collect every pinned source: manifests (`package.json`, `requirements.txt`,
`pyproject.toml`, `Gemfile`, `pom.xml`, `build.gradle`, `Cargo.toml`, etc.),
lockfiles, and container or action pins (for example `Dockerfile`, workflow
pins, or a version file). Record current versions, latest available patch or
minor, and the owning manifest.

Record supply-chain context when available: publisher or maintainer change,
yanked or deprecated status, abandonment signals, install scripts, bundled
binaries, provenance or attestation, registry source, and whether the package
is transitive. Treat these as risk signals requiring evidence, not automatic
vulnerability findings.

## Step 3 — Risk-grouped bumps

Order work by risk and reviewability:

1. **Security** — vulnerable direct or transitive dependencies where the
   package manager or advisory identifies the exposure (patch or minor that
   fixes the alert).
2. **Patch** — backwards-compatible fixes in direct dependencies.
3. **Minor** — new backwards-compatible features; check changelog and tests.
4. **Major or toolchain** — breaking changes, language or action major bumps;
   treat as a separate change set with explicit approval.

Keep each group small and focused. Do not bundle unrelated major bumps with
security fixes.

## Step 4 — Verify after each group

### Lockfile regeneration and churn inspection

Always use the ecosystem's deterministic update commands:

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

Regardless of ecosystem, the full-gate check MUST include `git diff <lockfile>` and confirm only the targeted package tree changed. uv/poetry/pip-tools are examples, not an exhaustive list; detect the project's actual lockfile tool and use its deterministic command.

After regeneration, run `git diff <lockfile>` and verify that only the targeted package and its direct dependency tree changed. Reject unexpected sweeping changes to unrelated packages.

- Ensure lockfiles are regenerated by the package manager, not hand-edited.
- Confirm tests still protect distinct behavior and that coverage or lint
  gates still pass.
- Inspect the diff for unexpected transitive changes.
- For schema or data-shape changes, use an additive expand → backfill →
  contract sequence when compatibility requires it. Keep old and new code
  valid at each deploy step, throttle backfills, isolate destructive drops or
  renames, and verify the rollback/down path before the next group.

## Step 5 — Document and propose

Update `CHANGELOG.md` when user-visible, and record version pins in the
relevant documentation. Keep the PR small, conventional, and linked to the
alert or issue when applicable. Stop and ask before changing pinning policy,
switching registries, or accepting a license that is not clearly
permissive.

## Boundaries and gotchas

- Check runtime engine requirements (`engines.node` in `package.json`, `requires-python` in `pyproject.toml`, Rust edition in `Cargo.toml`) before applying minor or major version bumps.
- Check package license changes on minor/major upgrades. If a dependency changes from a permissive license (MIT, Apache-2.0, BSD) to copyleft or proprietary (GPL, AGPL, SSPL, BSL), stop and request explicit approval.
- Do not downgrade or unpin a dependency to silence a warning.
- Do not accept a non-permissive license without explicit approval.
- Do not mix dependency bumps with feature or refactor work in the same
  commit.
- Do not create a remote, tag, or release without separate authorization.

## Relationship to neighboring skills

| Skill | Owns |
| :---- | :---- |
| **dependency-upgrade** (this) | Pinned dependency and lockfile upgrade workflow |
| `security-review` | Security boundary, secret, and threat-model review |
| `quality-hardening` | Bounded correctness fixes with regression coverage |
| `git-github-workflow` | Branch, commit, and PR hygiene |
