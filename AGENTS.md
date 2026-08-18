# Agent Guidance Kit — Agent Instructions

This repository is a portable library of agent skills. When working here:

- The canonical catalog lives in `skills/`; each skill is a self-contained
  `SKILL.md` following the Agent Skills format. The README's "Included skills"
  table is the index; the full adoption workflow is in
  [`docs/using-the-library.md`](docs/using-the-library.md).
- Run the full project gate before committing and again before pushing:
  `python3 scripts/validate_evaluations.py`,
  `python3 -m pytest scripts/test_validate_evaluations.py -q`,
  the README index check, and `ruff check scripts/`. See
  [`.github/workflows/check.yml`](.github/workflows/check.yml).
- Do not modify skill bodies, references, or evals without an explicit
  approved change pass. Reviews are read-only unless application is
  separately authorized.

## Mandatory adversarial review for PRs

Per adopting repository policy (see
[`skills/adversarial-pr-review/SKILL.md`](skills/adversarial-pr-review/SKILL.md)):

- Every branch that opens or updates a pull request MUST receive a completed
  fresh-context adversarial review **before any push** of that branch.
- After a PR is created, the gate is mandatory on **every later update push**
  until the review converges — the final pass reports no additional findings.
  A prior review does not cover later changes.
- The parent may not substitute its own self-review; at least one fresh,
  independent, read-only subagent reviewer is required.
- The mechanics and track matrix are owned by `adversarial-pr-review`; the
  branch/commit/PR hygiene steps are in
  [`skills/git-github-workflow/SKILL.md`](skills/git-github-workflow/SKILL.md).

### Blocked-review exception

If a fresh read-only subagent reviewer cannot be launched (harness limitation,
missing capability, or sandbox restriction), the review is **blocked**: do not
push the branch. Report the blocked review and the exact capability gap to the
user instead, and wait for explicit direction.

### Convergence evidence

A completed review is recorded as a compact verdict — `PASS` or up to three
anchored `path:line` findings — plus the review's commit range. Keep the
verdict available (session report, PR description, or tracked artifact) so a
later update push can confirm the final pass covered the current diff and
reported no additional findings.

## Review preferences (all harnesses)

This repository also carries the maintainer's review preferences in a Command
Code taste profile at [`.commandcode/taste/`](.commandcode/taste/). The taste
storage format is Command Code-specific, but the preferences are meant to be
considered by any harness:

- adversarial/diff reviews are performed by a **single fresh-context subagent**
  rather than the context that made the changes;
- the review must **converge** — no additional validated findings — before a
  push or PR proceeds;
- verdicts are compact and bounded: `PASS` or at most three anchored
  repo-relative `path:line` findings with severity and impact;
- review findings are applied as a separate, explicitly authorized pass, and
  the full batch is approved at once rather than item by item.

Non-Command Code harnesses should treat these as the maintainer's stated
preferences even though the taste file format is not natively read by them.
