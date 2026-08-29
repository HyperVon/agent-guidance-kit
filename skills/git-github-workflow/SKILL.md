---
name: git-github-workflow
description: >-
  Maintain local Git hygiene and GitHub collaboration with approval-gated
  branches, atomic commits, PR and issue hygiene, and release safety. Use when
  creating branches, committing, pushing, opening or reviewing pull requests,
  triaging issues, or changing repository GitHub settings.
---

# Git GitHub Workflow

Keep Git history readable and GitHub collaboration safe with explicit approval
gates. The agent proposes branches, commits, and PRs; it does not rewrite
history or publish without authority.

## Contract

- **Input:** intent (branch/commit/PR/issue/release), current `git status`,
  target base, `.github/*` templates, and applicable local guidance.
- **Output:** branch plan, atomic commit set, PR/issue draft, settings change
  proposal, and verification evidence — or a blocked report.
- **Owner:** local Git hygiene and GitHub collaboration workflow.
- **Non-goals:** architecture decisions, code review of diff content, or
  provider/model selection.
- **Side effects:** read-only until approval; afterward only `git branch`,
  `commit`, `push`, and `gh`/`API` calls the user explicitly authorized.

## Workflow

1. **Establish state and authority.** Read `git status --porcelain`, `git branch --show-current`,
   `git log --oneline -5`, remote, and protection rules. Resolve the canonical
   base from repository policy, existing PR metadata, the remote default, or an
   explicit user instruction, and determine whether a clean worktree is required.
   Confirm the user has authorized any `push`, `publish`, or `PR` creation;
   otherwise stop after the draft.

   **Worktree safety and pre-flight checklist:**
   - Run `git status --porcelain` to identify untracked, modified, and staged files.
   - If uncommitted changes exist that do not belong to the current task:
     - Ask the user whether to commit, stash (`git stash -u` to include untracked files), or discard.
     - Never run destructive commands (`git checkout -- .`, `git clean -fd`, `git reset --hard`) without explicit approval.
   - Confirm the target branch does not already exist locally or remotely (`git branch --list <name>`, `git ls-remote --heads origin <name>`).
2. **Plan the branch and commits.** Use the repository's established branch
   naming from the resolved base; when no convention exists, propose a concise
   purpose-based name. Keep commits atomic and conventional
   (`feat:`, `fix:`, `docs:`, `chore:`). Never use `reset --hard`,
   `filter-branch`, `rebase --force`, or history rewriting on shared branches
   without explicit approval.

   **Author identity verification:**
   - Inspect `git config user.name` and `git config user.email` (or `git var GIT_AUTHOR_IDENT`).
   - Confirm the email matches the user's intended public identity or GitHub privacy email (e.g. `<id>+<username>@users.noreply.github.com`).
   - If identity is unconfigured or misconfigured, propose the appropriate local config command (`git config user.name "..." && git config user.email "..."`) and wait for confirmation. Never commit with an auto-generated local hostname email.
3. **Draft the change.** Keep PRs small, describe user-visible change,
   motivation, scope/safety checklist, and verification (the project's gate, such as `make test`,
   `gh pr checks`). Use `.github/pull_request_template.md` and
   `ISSUE_TEMPLATE/*` when present. Link issues, update `CHANGELOG.md` when
   user-visible.
4. **Improve existing prompts when useful.** If the target has weak `AGENTS.md`,
   `CLAUDE.md`, `.cursor/rules`, or copilot instructions, propose paste-ready
   text-level improvements derived from catalog decision procedures rather than
   copying a parallel skill. Keep always-loaded files concise via
   `skill-optimizer`.
5. **Verify hygiene and target-local gates.** Check `git diff --stat`, relative
   links, no secrets or personal paths (using the target's documented hygiene
   check when one exists), and that the branch does not expose ignored runtime
   state such as `.kilo` or `.idea`. Discover the target repository's own
   documented format, lint, test, build, and coverage commands from its local
   guidance and build files, then run the smallest complete relevant gate.
    A project's own verification command (for example a `make` target) is an example, not a universal
    commands: never assume a helper, path, language toolchain, or quality
    threshold from the source project or from another repository. If no
    complete gate is available, report the exact checks that were run and the
    limitation rather than inventing or importing one.

   - *Run the target's complete gate before commit and push:* Run the target
     repository's full local verification gate (for example a `make` target or CI command) or its
     equivalent) before committing and again before pushing. The gate typically
     runs Markdown/guidance lint, structural validation, and secret scans. Treat a
     failing or skipped gate as a blocker: resolve the findings (or, for a genuine
     false positive, record the exact reason) before commit/push. Never commit or
     push with the gate red or skipped.
6. **Reconcile, verify, and freeze the publish candidate.** Fetch the resolved
   base from the approved remote and reconcile before the final gate or review.
   Record the reconciled `BASE_SHA` and candidate `HEAD_SHA`, then run the full
   repository gate against that exact state. Inspect local policy (for example
   `AGENTS.md` or `CONTRIBUTING.md`) and, when it requires
   `adversarial-pr-review`, invoke it on the exact `BASE_SHA...HEAD_SHA` diff
   before the initial push and every later update push. Require a completed
   fresh-context verdict and convergence evidence. Any later commit, amend,
   merge, rebase, conflict resolution, generated-file change, or other diff
   mutation invalidates the final gate and review and returns the workflow to
   this step. The review mechanics are owned by
   [adversarial-pr-review](../adversarial-pr-review/SKILL.md); this gate does not
   replace separate authorization to push.
7. **Publish only the frozen candidate with approval.** Confirm that HEAD still
   equals the recorded `HEAD_SHA` and that the current remote base tip still
   equals `BASE_SHA`; if either moved, return to step 6. Do not open or update a
   PR while a required gate is red, skipped, stale, or blocked. Push to the
   approved remote and branch, set upstream only when requested, and open the PR
   with `gh pr create` using the approved body. Report branch, commit, remote,
   reconciled base SHA, reviewed diff range, and checks.

## Boundaries and gotchas

- Never run `git add .` or `git add -A` from repository root. Explicitly stage only the files owned by the task (`git add path/to/file1 path/to/file2`).
- Check `git diff --cached` before committing to verify zero unintended files, debug logs, or credentials are staged.
- Use explicit issue closing keywords in PR bodies (`Fixes #123`, `Closes #456`) rather than vague issue references.
- Do not `push --force`, use `push --force-with-lease` on the resolved base or
  protected default branch, or rewrite published history without explicit
  approval and a backup branch.
- Do not use a quick or skipped variant of the gate as the pre-commit or pre-push
  check; run the full gate and confirm it passes before committing or pushing.
  Skipping lint or structural validation is where guidance edits most often fail.
- Before any authorized `push --force-with-lease` on a non-base branch or other
  history rewrite, create an explicit backup branch
  (`git branch backup/<branch>-<date>`) and name it in the report; never rely on
  the reflog alone.
- Before opening or updating a PR, fetch and reconcile the resolved base, then
  freeze and report the exact `BASE_SHA...HEAD_SHA` range that passed the final
  gate and any required review.
- Do not commit secrets, `.env`, `id_rsa`, `*.pem`, or personal filesystem
  paths. Redact examples.
- Do not create a remote, tag, or release (`git tag`/`gh release`) without
  separate explicit authorization per the project's release documentation (for example `docs/release.md` when present).
- When local policy requires adversarial review, do not push a branch intended
  to open or update a PR without a completed fresh-context review of its final
  diff and convergence evidence; a prior review does not cover later changes.
- Prefer `AGENTS.md` hierarchy over adding duplicate harness entrypoints.
- Keep commits focused: one logical change per commit, no bundled refactors.

## Report and stop condition

Report: branch/base, commit list, PR/issue draft, files changed, hygiene
results, exact commands run, and what was not run. Stop and ask when the
worktree is dirty in a way that would be lost, the base has diverged, an
approval is missing for a destructive or publishing action, or the next step
requires credentials. Do not claim a PR is ready merely because a draft exists.
