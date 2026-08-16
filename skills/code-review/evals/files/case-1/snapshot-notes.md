# Snapshot notes

## What this directory is

A capture of the working tree at the tip of `fix/user-lookup-npe`, taken from
the review workspace.

## What is included

- All application sources at the branch tip (`app.py`, `auth.py`, `users.py`,
  `validation.py`, `db.py`, `errors.py`, `settings.py`)
- `docs/`, `tests/`, `requirements.txt`, CI workflow
- `PR-214.md` — the pull-request description as submitted
- `pr-214.partial.patch` — partial diff export (see below)

## What is not included

- `.git` metadata. There is no local object store, no `main` ref, and no merge
  base in this capture, so pre-change revisions of the sources cannot be
  recovered from this directory.
- CI logs or test output from the branch. No checks were executed while taking
  the capture.
- The `users.py` and `auth.py` hunks of the diff: the patch export was
  truncated by the export tool at a size limit and only the `app.py` and
  `validation.py` hunks were written.
- Production database access and the backfill job's reconciliation report.
