# Routing experiment semantics

The corrected methodology distinguishes three experiments. They have different
baselines and answer different questions; do not collapse them all into a single
"WITH-SKILL vs BASELINE" comparison.

## A. Routing availability experiment

- **Surfaces:** target routing entry *present* vs target routing entry
  *absent* (removed from the generated catalog).
- **Question:** does having this skill *available* cause the harness to select
  the correct owner?
- **Baseline condition:** the same catalog with the target skill removed. The
  task fixture is identical; only the routing projection differs.
- **Typical assertions:** a `matching` request selects the target when present
  and does not when absent (fallbacks allowed); a `neighboring` request selects
  the correct owner in **both** conditions (removing the target must not change
  the owner selection); an `ambiguous` request clarifies or states a
  documented tie-breaker in both conditions.
- **Graded from:** harness-selection evidence (loaded-skill manifest, routing
  log, named tool call). Worker prose explaining the choice is secondary.

## B. Routing description regression experiment

- **Surfaces:** candidate target **description** vs the prior-version
  **description** (both present in the catalog).
- **Question:** did this description change improve or regress routing?
- **Baseline condition:** the prior description string for the target skill.
- **Use:** when tuning a skill's `description` (its discoverability surface)
  and you want to measure the delta, not merely presence/absence.

## C. Execution efficacy experiment

- **Surfaces:** target guidance **loaded** vs harness default **without** target
  guidance.
- **Question:** once activated, does this skill improve task execution?
- **Baseline condition:** harness default with no target skill text, identity,
  or metadata — verified absent, not merely unmentioned.
- **Graded from:** worker output against the frozen `execution.assertions`.
- **Not** evidence about routing.

## Generating the routing projection

The catalog is produced by `scripts/build_routing_catalog.py` from each skill's
frontmatter. It is the harness routing surface and is **never** committed inside
a task fixture:

```bash
python3 scripts/build_routing_catalog.py                      # target-present
python3 scripts/build_routing_catalog.py --target-absent code-review   # baseline
```

The same task fixture is reused across conditions; only the generated catalog
differs. This keeps the task identical between the target-present and
target-absent conditions so any selection difference is attributable to the
routing surface, not to fixture content.
