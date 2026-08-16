# Fixture: case 5 (generator)

## What this fixture provides

A real git repository on branch `feature/export-endpoint`, with `main` as the
merge base, containing a `REVIEW.md` that records three P1 findings and the
code those findings describe.

## Generating it

Run the generator from an empty directory:

```
mkdir -p /tmp/code-review-case-5 && cd /tmp/code-review-case-5
bash <path-to>/setup.sh
```

The generator:

- runs `git init` and creates `main`, then branches `feature/export-endpoint`
- commits with a fixture-local identity passed per invocation
  (`git -c user.name=... -c user.email=...`), so global and user git
  configuration is never modified
- pins author and committer dates, so repeated runs produce the same tree and
  the same history shape
- refuses to run if `.git` already exists in the working directory

Commit graph after a run:

```
* Add review notes for the export endpoint   (feature/export-endpoint)
* Add record export endpoint with pagination
* Reporting API: summary endpoints, router, api key checks   (main)
```

## Baseline state

The generated suite passes before any edit:

```
python3 -m unittest discover -s tests -t .   # 25 tests, OK
make test                                    # same command
```

The service uses the standard library only, so no dependency install is
required.

## `snapshot/`

`snapshot/` holds byte-identical copies of the generated working-tree files so
the fixture content can be inspected or diffed without running the generator.
It is a mirror for inspection only — `setup.sh` is the canonical source, and
`snapshot/` has no git history. Regenerate the mirror by running the generator
in an empty directory and copying everything except `.git`.
