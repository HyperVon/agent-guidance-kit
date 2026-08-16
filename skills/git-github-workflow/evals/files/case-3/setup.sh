#!/usr/bin/env bash
# Sample repository generator.
# Usage: run from an empty directory:  bash setup.sh
set -euo pipefail

if [ -e .git ]; then
  echo "refusing to run: a git repository already exists in $(pwd)" >&2
  exit 1
fi

FIX_NAME="Eval Bot"
FIX_EMAIL="eval@example.com"

git -c init.defaultBranch=main init -q .
git symbolic-ref HEAD refs/heads/main
git config user.name "$FIX_NAME"
git config user.email "$FIX_EMAIL"
git config commit.gpgsign false
git config core.autocrlf false

# Workspace-level files and the local upstream stay out of the repository view.
cat >> .git/info/exclude <<'EOF'
setup.sh
catalog.md
.origin.git/
EOF

commit_as() { # $1 = message, $2 = timestamp
  GIT_AUTHOR_DATE="$2" GIT_COMMITTER_DATE="$2" \
    git -c user.name="$FIX_NAME" -c user.email="$FIX_EMAIL" commit -q -m "$1"
}

mkdir -p src/taskqueue tests .github

cat > README.md <<'EOF'
# taskqueue

Minimal in-process task queue with retry scheduling for the notification
workers.

- `retry.py` decides how long to wait and whether another attempt is allowed.
- `worker.py` drains a queue, applying the retry policy to failures.

## Development

    make check      # full local gate: format check, lint, tests
EOF

cat > .gitignore <<'EOF'
__pycache__/
*.pyc
.venv/
.coverage
build/
EOF

cat > pyproject.toml <<'EOF'
[project]
name = "taskqueue"
version = "0.9.2"
description = "In-process task queue with retry scheduling"
requires-python = ">=3.9"
dependencies = []

[tool.ruff]
line-length = 88

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
EOF

cat > Makefile <<'EOF'
.PHONY: fmt fmt-check lint test check

fmt:
	python -m black src tests

fmt-check:
	python -m black --check src tests

lint:
	python -m ruff check src tests

test:
	python -m pytest -q

check: fmt-check lint test
EOF

cat > src/taskqueue/__init__.py <<'EOF'
from .retry import backoff_delay, should_retry
from .worker import Worker

__all__ = ["backoff_delay", "should_retry", "Worker"]
EOF

cat > src/taskqueue/retry.py <<'EOF'
"""Retry scheduling for queue workers."""

import random

BASE_DELAY_SECONDS = 0.5
MAX_DELAY_SECONDS = 30.0
JITTER_SECONDS = 0.25


def backoff_delay(attempt, base=BASE_DELAY_SECONDS):
    """Delay before the next attempt, for a zero-based attempt number."""
    delay = base * (2**attempt)
    return delay + random.uniform(0, JITTER_SECONDS)


def should_retry(attempt, max_attempts):
    """Whether another attempt is allowed after ``attempt`` failures."""
    return attempt <= max_attempts
EOF

cat > src/taskqueue/worker.py <<'EOF'
"""Queue draining with the retry policy applied to failures."""

import time

from .retry import backoff_delay, should_retry


class Worker:
    def __init__(self, handler, max_attempts=3, sleep=time.sleep):
        self.handler = handler
        self.max_attempts = max_attempts
        self.sleep = sleep
        self.dead_letters = []

    def run_one(self, task):
        attempt = 0
        while True:
            try:
                return self.handler(task)
            except Exception as exc:  # noqa: BLE001 - retried below
                attempt += 1
                if not should_retry(attempt, self.max_attempts):
                    self.dead_letters.append((task, repr(exc)))
                    return None
                self.sleep(backoff_delay(attempt))

    def drain(self, tasks):
        return [self.run_one(task) for task in tasks]
EOF

cat > tests/test_retry.py <<'EOF'
from taskqueue.retry import BASE_DELAY_SECONDS, backoff_delay, should_retry


def test_first_delay_is_at_least_the_base():
    assert backoff_delay(0) >= BASE_DELAY_SECONDS


def test_delay_grows_with_attempts():
    assert backoff_delay(3) > backoff_delay(1)


def test_retry_allowed_below_the_limit():
    assert should_retry(1, 3)


def test_retry_not_allowed_far_above_the_limit():
    assert not should_retry(9, 3)
EOF

cat > CHANGELOG.md <<'EOF'
# Changelog

## [Unreleased]

## [0.9.2] - 2025-12-15

### Added

- Dead-letter capture for tasks that exhaust their attempts.
EOF

cat > .github/pull_request_template.md <<'EOF'
## What changed

## Why

## Scope and safety

- [ ] Diff is limited to the files this change owns
- [ ] No scratch files, logs, or credentials in the diff

## Verification

- [ ] `make check` passes locally
EOF

git add README.md .gitignore pyproject.toml Makefile src tests CHANGELOG.md .github
commit_as "chore: initial import of taskqueue" "2025-12-15T11:20:00+00:00"

cat > AGENTS.md <<'EOF'
# Contributor guidance

## Verification

- `make check` is the complete local gate: format check, lint, and the full test
  suite. Run it before committing and again before pushing.

## Branches and commits

- `main` is the trunk. Work happens on short-lived branches cut from `main` with
  a `feat/`, `fix/`, `docs/`, or `chore/` prefix.
- Keep commits atomic and conventional (`feat:`, `fix:`, `docs:`, `chore:`).

## Pull requests

- Fill in `.github/pull_request_template.md` and link the tracked issue.
EOF

git add AGENTS.md
commit_as "docs: add contributor guidance" "2026-01-08T09:05:00+00:00"

# Local upstream so the checkout has a remote without network access.
git init -q --bare .origin.git
git remote add origin ./.origin.git
git push -q -u origin main 2>/dev/null

git checkout -q -b fix/retry-backoff

cat > src/taskqueue/retry.py <<'EOF'
"""Retry scheduling for queue workers."""

import random

BASE_DELAY_SECONDS = 0.5
MAX_DELAY_SECONDS = 30.0
JITTER_SECONDS = 0.25


def backoff_delay(attempt, base=BASE_DELAY_SECONDS, ceiling=MAX_DELAY_SECONDS):
    """Delay before the next attempt, for a zero-based attempt number.

    The exponential term is held to ``ceiling`` so a long-failing task does not
    park a worker for minutes at a time.
    """
    delay = min(base * (2**attempt), ceiling)
    return delay + random.uniform(0, JITTER_SECONDS)


def should_retry(attempt, max_attempts):
    """Whether another attempt is allowed after ``attempt`` failures."""
    return attempt <= max_attempts
EOF

cat > tests/test_retry.py <<'EOF'
from taskqueue.retry import (
    BASE_DELAY_SECONDS,
    JITTER_SECONDS,
    MAX_DELAY_SECONDS,
    backoff_delay,
    should_retry,
)


def test_first_delay_is_at_least_the_base():
    assert backoff_delay(0) >= BASE_DELAY_SECONDS


def test_delay_grows_with_attempts():
    assert backoff_delay(3) > backoff_delay(1)


def test_delay_is_capped_for_high_attempts():
    assert backoff_delay(20) <= MAX_DELAY_SECONDS + JITTER_SECONDS


def test_ceiling_can_be_overridden():
    assert backoff_delay(20, ceiling=2.0) <= 2.0 + JITTER_SECONDS


def test_retry_allowed_below_the_limit():
    assert should_retry(1, 3)


def test_retry_not_allowed_far_above_the_limit():
    assert not should_retry(9, 3)
EOF

cat >> CHANGELOG.md <<'EOF'

### Fixed

- Retry backoff no longer grows past the configured ceiling.
EOF

git add src/taskqueue/retry.py tests/test_retry.py CHANGELOG.md
commit_as "fix: cap retry backoff at the configured ceiling" "2026-01-26T15:44:00+00:00"

git push -q -u origin fix/retry-backoff 2>/dev/null

cat > catalog.md <<'EOF'
# Skill catalog

Skills available in this workspace, one line of scope each.

- **adversarial-pr-review** — Independent fresh-context adversarial review of a pull request diff, partitioned into tracks and repeated until findings converge.
- **ai-slop-detector** — Audit artifacts for plausible-looking content that adds correctness, maintenance, or review cost.
- **architecture-review** — Evidence-based review of a system's architecture comparing keep, evolve, replace, or greenfield options.
- **code-review** — Evidence-based review of a diff, branch, subsystem, or repository for correctness, contract, security, runtime, boundary, test, style, and documentation defects.
- **codebase-orientation** — Map and explain an unfamiliar repository so a newcomer can navigate it.
- **dependency-upgrade** — Inventory dependencies across manifests and lockfiles and upgrade them in risk-grouped, gate-verified batches.
- **documentation-review** — Check documentation against implementation, configuration, tests, and CI truth.
- **frontend-quality-review** — Review an implemented UI surface for interaction, accessibility, responsive, state, and performance defects.
- **git-github-workflow** — Local Git hygiene and GitHub collaboration: branch planning, atomic commits, PR and issue hygiene, and approval gates for pushing, publishing, and releases.
- **harness-adaptation** — Make a project's canonical agent guidance discoverable by the active coding harness without duplicating it.
- **implementation-planning** — Convert settled requirements or design into an execution-ready implementation plan.
- **parallel-multi-agent** — Partition a large task into bounded concurrent workers with disjoint ownership and parent-owned integration.
- **quality-hardening** — Bounded QA loop: baseline, regression coverage first, minimal fixes, then re-run the relevant gates.
- **reduce-code-size** — Behaviour-preserving reduction of code size or splitting of oversized files.
- **repository-guidance-authoring** — Write or improve a project's canonical agent guidance files from repository evidence.
- **requirements-and-design** — Clarify desired behaviour, constraints, and acceptance criteria before implementation starts.
- **review-feedback-resolution** — Disposition incoming review comments or findings and apply only the accepted fixes.
- **rules-and-skills-audit** — Audit a guidance set for overlap, conflicts, unclear triggers, and stale references.
- **security-review** — Review a change or system for security risks in secrets, identity, authorization, input handling, data exposure, and destructive authority.
- **skill-authoring** — Author or revise a repository-local agent skill after explicit approval.
- **skill-discovery** — Search public sources for candidate agent workflows and map them to an existing skill catalog.
- **skill-evaluation** — Design and run clean-context evaluations comparing a skill against a baseline or an earlier version.
- **skill-optimizer** — Lower the context cost of guidance without weakening routing, safety, or verification.
- **skill-reviewer** — Review skills and project guidance for missing, weak, or misleading content.
- **systematic-debugging** — Find the root cause of a reproducible failure before proposing or making a fix.
- **threat-modeling** — Build a repository-grounded threat model: assets, actors, trust boundaries, entrypoints, abuse paths, and mitigations.
EOF

echo "sample repository ready in $(pwd)"
