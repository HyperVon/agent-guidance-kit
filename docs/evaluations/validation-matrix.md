# Validation matrix

This matrix tracks where skill evaluations have been executed in isolated clean-context runs (`skill` vs `no-skill` or `previous version`) and confirmed to perform **better than baseline** with graded assertion evidence. It is updated whenever an evaluation is run and the result file is added under `docs/evaluations/results/`. Raw model outputs remain in ignored workspaces; only sanitized summaries and this matrix are committed.

* `✓` — skill condition passed all `matching`/`neighboring`/`ambiguous` assertions and outperformed baseline (`skill_pass == total`, `baseline_pass < total`, `better=true`, decision `KEEP`/`KEEP_PROVISIONAL`).
* `=` — both conditions passed (no discriminating advantage, `KEEP_PROVISIONAL`).
* `–` — not yet tested on that model/harness.
* Links point to the sanitized report (`results/*.md` — human-readable) and the machine-readable result file (`results/*.json` — validated by `scripts/validate_repository.py`).

| Skill | `gpt-5.6-luna` / Codex (`low`) | `gpt-5.6-sol` / Codex (`xhigh`) | `muse-spark-1.2-contributor` / `muse-code` (`0.1.0`) |
| :--- | :--- | :--- | :--- |
| `agent-guidance-maintenance` | [✓](2026-08-10-catalog-expansion.md) | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |
| `ai-slop-detector` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |
| `architecture-review` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |
| `bootstrap-project` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |
| `code-review` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |
| `documentation-review` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |
| `harness-adaptation` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |
| `parallel-multi-agent` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |
| `quality-hardening` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |
| `reduce-code-size` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |
| `rules-and-skills-audit` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |
| `security-review` | [✓](2026-08-10-catalog-expansion.md) | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |
| `skill-authoring` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |
| `skill-evaluation` | [✓](2026-08-10-catalog-expansion.md) | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |
| `skill-optimizer` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |
| `skill-reviewer` | [✓](2026-08-10-external-skill-intake.md) (`fab98c2`) | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |
| `systematic-debugging` | [=](2026-08-10-catalog-expansion.md) / [✓](2026-08-11-systematic-debugging-fixture.md)† | [=](2026-08-11-systematic-debugging-fixture.md)† | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) |

† `systematic-debugging` fixture evaluation (order-recovery) passed 4/4 in both conditions for `luna` and `sol` on Codex — no discriminating advantage, decision `KEEP_PROVISIONAL`. See [2026-08-11-systematic-debugging-fixture.md](2026-08-11-systematic-debugging-fixture.md).

## How to read the matrix

* Every `✓` corresponds to a result file under `docs/evaluations/results/` with `schema_version`, `harness`, `model`, `baseline`, per-case `skill_pass`/`baseline_pass`/`better`, and `decision`. The repository validator checks that the markdown links match the JSON records and that `better` is only claimed when `skill_pass > baseline_pass` on meaningful assertions.
* `–` does not mean the skill is broken — it means that model/harness combination has not yet been measured. Add a run to fill the column.

## How to add a run

1. Follow `skill-evaluation` to run each `evals/evals.json` case twice (`with-skill` vs `baseline`) in a dedicated empty directory containing only `evals/files/*`.
2. Grade each `assertions` entry with quoted evidence, perform human review, and record timing/tokens if available.
3. Add a result file `docs/evaluations/results/YYYY-MM-DD-<model>-<harness>.json` (or `<skill>-<model>-<harness>.json` for single-skill runs) conforming to the schema in `docs/evaluations/results/README.md`.
4. Update this matrix: change `–` to `✓`/`=` and link to the new result file and any sanitized report.
5. Run `make check` — the evaluation-result validator will verify the JSON shape, `skill_name` matches an existing skill, `model`/`harness` are recorded, and linked files exist.

## Current coverage

* `17` skills have `evals/evals.json` definitions (structural check: `Validated 17 skills ... evaluation definitions: 17 present`).
* Historical runs: `2026-08-10` (`gpt-5.6-luna` low, 4 skills), `2026-08-10` external intake (`gpt-5.6-luna` low, `skill-reviewer`), `2026-08-11` fixture (`gpt-5.6-luna` low + `gpt-5.6-sol` xhigh, `systematic-debugging`), `2026-08-11` (`muse-spark-1.2-contributor` / `muse-code` 0.1.0, all 17).
* Latest full run `2026-08-11-muse-spark-1.2-contributor-muse-code.json` confirms all 17 outperformed baseline on the committed assertion sets in isolated workspaces (`/tmp/eval-batch-1`, `/tmp/eval-batch-2`, `/tmp/skill-evals-batch3`, `/tmp/agk-evals-batch4`). One run per condition per model — not a statistical benchmark.
