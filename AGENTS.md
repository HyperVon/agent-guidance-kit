# Agent Guidance Kit — Agent Instructions

This repository is a portable library of agent skills. When working here:

- The canonical catalog lives in `skills/`; each skill is a self-contained
  `SKILL.md` following the Agent Skills format. The README's "Included Skills"
  table is the index; the full adoption workflow is in
  [`docs/using-the-library.md`](docs/using-the-library.md).
- Keep skills portable: use project-neutral names, state triggers and
  boundaries, and put deeper material in skill-local `references/` files.
- Do not modify ordinary skill bodies or references for cleanup, style, or
  benchmark results. Skill changes require an explicitly approved change pass.
- Evaluation corpus, methodology, evidence, and execution belong to
  `HyperVon/agent-guidance-kit-evals`; do not add evaluator code or canonical
  evaluation data back to AGK.

## Deterministic Gate

Run the product-only gate before committing and again before pushing:

```text
python3 scripts/validate_catalog.py
python3 -m unittest discover -s scripts -p 'test_*.py' -q
ruff check scripts/
git diff --check
```

The gate checks skill structure and frontmatter, README catalog integrity,
repository-relative Markdown links, and the absence of canonical evaluator
roots. It does not require the eval repository, a model, Kilo, Promptfoo,
Docker, or network access to an evaluator.

## Mandatory Adversarial Review for PRs

Per repository policy and
[`skills/adversarial-pr-review/SKILL.md`](skills/adversarial-pr-review/SKILL.md):

- Every branch that opens or updates a pull request MUST receive a completed
  fresh-context adversarial review before any push.
- After a PR is created, review the complete update delta before every later
  push until the review converges with no additional findings.
- The parent may not substitute its own self-review; at least one fresh,
  independent, read-only subagent reviewer is required.
- Review findings are applied only in a separately authorized change pass.
- Record a compact `PASS` or up to three anchored findings with the reviewed
  commit range.

If a fresh read-only reviewer cannot be launched, the review is blocked: do not
push and report the exact capability gap.
