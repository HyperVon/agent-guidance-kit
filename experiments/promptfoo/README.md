# Promptfoo compatibility spike (AGK)

A small, isolated Promptfoo-backed prototype that exercises representative
parts of the AGK evaluation corpus to answer:

> Can Promptfoo replace most of the home-grown evaluation engine while
> preserving the experimental semantics and evidence quality that matter?

This is a spike, NOT a migration. The existing evaluator
(`scripts/run_*`, `scripts/evaluation/**`, `scripts/validators/**`,
`Dockerfile.eval`) is untouched and remains the reference implementation.
The decision report is `REPORT.md`.

## Layout

```
providers/       thin kilo-CLI providers (routing, execution, rubric judge)
generators/      canonical-corpus -> Promptfoo test projections
assertions/      routing protocol + baseline-fairness scope policy
analysis/        AGK routing metrics + v1-vs-v2 comparison
lib/             paths, hashing wrappers, workspace materialization
configs/         one promptfooconfig per experiment
generated/       GENERATED test files (+ .meta.json provenance)
tests/           unittest suite for the thin layer only
.results/        exported eval results and comparison reports (not tracked)
```

## Engine facts (promptfoo 0.122.0, pinned in package.json)

* custom Python provider: `file://provider.py[:func]` returning
  `{output, error, metadata}`; `context.vars` carries per-row identity;
* repetitions are explicit generated rows (`rep` var), not `--repeat`;
* caching must be disabled per run (`--no-cache` / config) — repeated
  identical prompts otherwise collapse;
* `-o file.json` exports the full row set used by `analysis/`.
* relative `file://` paths resolve against the CONFIG file directory, hence
  `../` prefixes from `configs/*.yaml`.

## Run

```bash
npm install                      # pinned promptfoo

# Layer A - development confusion set (17 cases x 3 reps)
python3 generators/routing_cases.py --set review-family --reps 3
./node_modules/.bin/promptfoo eval -c configs/routing-development.yaml \
    --no-cache -o .results/routing-dev.json --no-progress-bar
python3 analysis/routing_metrics.py --results .results/routing-dev.json \
    --skills code-review security-review architecture-review \
        adversarial-pr-review review-feedback-resolution \
        frontend-quality-review documentation-review threat-modeling \
        implementation-planning systematic-debugging

# Layer B - execution efficacy (independent workspaces per condition)
python3 generators/skill_cases.py
AGK_PF_RUN_ID=exec ./node_modules/.bin/promptfoo eval \
    -c configs/execution.yaml --no-cache -o .results/execution.json \
    --no-progress-bar

# Regression (candidate vs reference SKILL.md revision)
python3 generators/skill_cases.py --regression
./node_modules/.bin/promptfoo eval -c configs/regression.yaml \
    --no-cache -o .results/regression.json --no-progress-bar

# FROZEN HOLDOUT - run once, never tune against it
python3 generators/routing_cases.py --set review-discrim-1 --reps 3
./node_modules/.bin/promptfoo eval -c configs/routing-holdout.yaml \
    --no-cache -o .results/routing-holdout.json --no-progress-bar

# Comparison against the existing evaluator's committed evidence
python3 analysis/compare_v1_v2.py routing \
    --v1 ../../.eval-evidence/layerA-review-family-v4.json \
    --v2 .results/routing-dev.json \
    --corpus ../../evaluations/confusion-sets/review-family.json \
    --label development --out .results/compare-routing-dev.md

python3 -m unittest tests.test_spike
```

## Invariants preserved from the existing evaluator

* failed model invocations are recorded separately and can never become
  null observations; `attempted = successful + failed`;
* an explicit null selection is a valid successful observation;
* expected routes/prompts come from the canonical corpus files (hash-checked
  in `generated/*.meta.json`);
* baseline/placebo rows are graded only on shared-outcome and
  universal-safety assertions;
* activation evidence in Layer B is labeled `forced`; Layer C is `not_run`.

## Operational notes discovered during the spike

* spawn `kilo run` with BOTH `cwd=` and `PWD` in the child env — Kilo
  resolves project skill discovery from `PWD`;
* use `--auto` for agentic execution cases (tool permissions);
* pure-text routing calls need neither;
* python assertion failures set top-level `error` on rows while keeping a
  parseable decision in `response.output` — classification must key off
  `response.error` (see `analysis/routing_metrics.classify_row`).
