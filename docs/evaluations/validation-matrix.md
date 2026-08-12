# Validation matrix

This matrix tracks where skill evaluations have been executed in isolated clean-context runs (`skill` vs `no-skill` or `previous version`) and confirmed to perform **better than baseline** with graded assertion evidence. It is updated whenever an evaluation is run and the result file is added under `docs/evaluations/results/`. Raw model outputs remain in ignored workspaces; only sanitized summaries and this matrix are committed.

* `✓` — skill condition passed all `matching`/`neighboring`/`ambiguous` assertions and outperformed baseline (`skill_pass == total`, `baseline_pass < total`, `better=true`, decision `KEEP`/`KEEP_PROVISIONAL`).
* `=` — both conditions passed (no discriminating advantage, `KEEP_PROVISIONAL`).
* `–` — not yet tested on that model/harness.
* Links point to the sanitized report (`results/*.md` — human-readable) and the machine-readable result file (`results/*.json` — validated by `scripts/validate_repository.py`).

| Skill | `gpt-5.6-luna` / Codex (`low`) | `gpt-5.6-sol` / Codex (`xhigh`) | `muse-spark-1.2-contributor` / `muse code` (`xhigh`, `0.1.0`) | `tencent/hy3:free` / `Kilo` (`default`) |
| :--- | :--- | :--- | :--- | :---: |
| `agent-guidance-maintenance` | [✓](2026-08-10-catalog-expansion.md) | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `ai-slop-detector` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `architecture-review` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `bootstrap-project` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `code-review` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `documentation-review` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `harness-adaptation` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `parallel-multi-agent` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `quality-hardening` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `reduce-code-size` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `rules-and-skills-audit` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `security-review` | [✓](2026-08-10-catalog-expansion.md) | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `skill-authoring` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `skill-evaluation` | [✓](2026-08-10-catalog-expansion.md) | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `skill-optimizer` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `catalog-discovery` | – | – | [✓](results/2026-08-12-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-12-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `git-github-workflow` | – | – | [✓](results/2026-08-12-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-12-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `skill-reviewer` | [✓](2026-08-10-external-skill-intake.md) (`fab98c2`) | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `systematic-debugging` | [=](2026-08-10-catalog-expansion.md) / [✓](2026-08-11-systematic-debugging-fixture.md)† | [=](2026-08-11-systematic-debugging-fixture.md)† | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `upstream-contribution` | – | – | [✓](results/2026-08-12-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-12-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) |
| `adversarial-pr-review` | – | – | [✓](results/2026-08-12-muse-spark-1.2-contributor-muse-code-eval-rerun-3.json) · [human](results/2026-08-12-muse-spark-1.2-contributor-muse-code-eval-rerun-3.md) | – |
| `dependency-upgrade` | – | – | [✓](results/2026-08-12-muse-spark-1.2-contributor-muse-code-eval-rerun-3.json) · [human](results/2026-08-12-muse-spark-1.2-contributor-muse-code-eval-rerun-3.md) | – |
| `runtime-router-bridge` | – | – | – | – |

† `systematic-debugging` fixture evaluation (order-recovery) passed 4/4 in both conditions for `luna` and `sol` on Codex — no discriminating advantage, decision `KEEP_PROVISIONAL`. See [2026-08-11-systematic-debugging-fixture.md](2026-08-11-systematic-debugging-fixture.md).

## How to read the matrix

* Every `✓` corresponds to a result file under `docs/evaluations/results/` with `schema_version`, `harness`, `model`, `baseline`, per-case `skill_pass`/`baseline_pass`/`better`, and `decision`. The repository validator checks that the markdown links match the JSON records and that `better` is only claimed when `skill_pass > baseline_pass` on meaningful assertions.
* `–` does not mean the skill is broken — it means that model/harness combination has not yet been measured. Add a run to fill the column.

## How to add a run

The human interface is conversation only — ask the agent to follow `skill-evaluation`; the agent executes all steps and the human does not need to run scripts manually.

1. Agent follows `skill-evaluation` to run each `evals/evals.json` case twice (`with-skill` vs `baseline`) in a dedicated empty directory containing only `evals/files/*`.
2. Agent grades each `assertions` entry with quoted evidence, performs human review, and records timing/tokens if available.
3. Agent adds a result file `docs/evaluations/results/YYYY-MM-DD-<model>-<harness>.json` (or `<skill>-<model>-<harness>.json` for single-skill runs) conforming to the schema in `docs/evaluations/results/README.md`.
4. Agent updates this matrix: change `–` to `✓`/`=` and link to the new result file and any sanitized report.
5. Agent regenerates `SUMMARY.md` with `python3 scripts/generate_evaluation_summary.py --write`.
6. Agent runs `make check` — the evaluation-result validator verifies the JSON shape, `skill_name` matches an existing skill, `model`/`harness` are recorded, linked files exist, and `SUMMARY.md` is fresh.

## Current coverage

* `23` skills have `evals/evals.json` definitions (structural check: `Validated 23 skills ... evaluation definitions: 23 present`).
* `22/23` skills have at least one executed evaluation; `runtime-router-bridge` has designed cases but no executed result yet.
* Historical runs: `2026-08-10` (`gpt-5.6-luna` low, 4 skills), `2026-08-10` external intake (`gpt-5.6-luna` low, `skill-reviewer`), `2026-08-11` fixture (`gpt-5.6-luna` low + `gpt-5.6-sol` xhigh, `systematic-debugging`), `2026-08-11` (`muse-spark-1.2-contributor` `xhigh` / `muse code` 0.1.0, 17 skills), `2026-08-12` (`muse-spark-1.2-contributor` `xhigh` / `muse code` 0.1.0, 3 skills).
* Latest runs `2026-08-11-muse-spark-1.2-contributor-muse-code.json` (17 skills), `2026-08-12-muse-spark-1.2-contributor-muse-code.json` (3 skills), and `2026-08-12-muse-spark-1.2-contributor-muse-code-eval-rerun-3.json` (2 skills, 3 assertions, prompt wording cleaned to review-only) together confirm all 22 previously evaluated skills outperformed baseline on the committed assertion sets in isolated workspaces. A full fresh run under `Kilo` / `tencent/hy3:free` (`default`, `2026-08-12-tencent-hy3-free-kilo.json`, 20 skills) also confirms all 20 outperformed baseline in isolated workspaces (`/tmp/agk-evals-2026-08-12-kilo/*`). (`/tmp/eval-batch-1`, `/tmp/eval-batch-2`, `/tmp/skill-evals-batch3`, `/tmp/agk-evals-batch4`, `/tmp/agk-evals-2026-08-12-*`). One run per condition per model — not a statistical benchmark; effort level (`low` vs `xhigh`) can change results dramatically, so it is recorded per result file.
