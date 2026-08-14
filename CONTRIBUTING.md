# Contributing

Contributions should keep the kit small, portable, and evidence-based.

## Before changing guidance

1. Read `AGENTS.md`, `.agents/AGENTS.md`, and `.agents/OPERATING.md`.
2. Identify the current owner of the behavior.
3. Prefer improving that owner over creating a parallel rule or skill.
4. Keep technology and domain policy in target repositories unless it clearly
   generalizes without becoming generic textbook advice.

## New skill bar

A new skill needs a distinct trigger, owner, non-goals, inputs, outputs, side
effects, stop condition, and verification contract. Its frontmatter description
must make neighboring routing unambiguous. Keep `SKILL.md` concise and move rare
variants or long examples to directly linked references.

## Scripts

Target-facing scripts must be deterministic, network-free, standard-library
Python, and safer than asking an LLM to repeat the same mechanical operation.
A repository-only validator may use a small declared development dependency
when it materially improves format validation. Add tests for path, symlink,
collision, partial-apply, and malformed-input behavior as applicable.

## Public hygiene

Use placeholders in examples. Do not add personal paths, usernames, hostnames,
credentials, account data, private repository URLs, logs, databases, or runtime
configuration.

## Verification

Run `python scripts/setup_dev.py` once, then run `scripts/check.py` with the
virtual environment's Python and inspect the complete diff. `make setup` and
`make check` are optional macOS/Linux conveniences. The complete check includes
required Markdown lint plus Python lint and formatting checks; fix every
finding before committing or pushing. Do not publish, push, or open a pull
request unless the repository owner explicitly asks.

For faster inner loop, use `python scripts/check.py --quick` (skips
markdownlint and `agentskills` validate). Prefer the full `make check` before
push. Before every push that opens or updates a pull request, also complete
the required `adversarial-pr-review` workflow in a fresh independent subagent
context against the final diff. Repeat it after authorized fixes until a final
pass reports no additional findings; the full `make check` does not substitute
for that review. If you use pre-commit,
`pre-commit install` mirrors the format and hygiene gates
locally (`ruff`, `validate_repository.py`, `public_hygiene_check.py`,
`markdownlint`).
