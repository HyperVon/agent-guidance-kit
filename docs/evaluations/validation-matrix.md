# Validation matrix

This matrix tracks where skill evaluations have been executed in isolated clean-context runs (`skill` vs `no-skill` or `previous version`) and confirmed to perform **better than baseline** with graded assertion evidence. A valid comparison requires two genuinely independent fresh workers or harness sessions; a single agent instructed to answer as if it had not seen the skill does not qualify. Results recorded before the independent-worker protocol was added are historical evidence only and do not prove that boundary from their committed metadata; rerun them before relying on them for a strong claim. Raw model outputs remain in ignored workspaces; only sanitized summaries and this matrix are committed.

* `✓` — a protocol-compliant, discriminating positive result where the guided condition outperformed baseline on at least one meaningful frozen assertion (`better=true`, `overall_better=true`, decision `KEEP`/`KEEP_PROVISIONAL`). A result where the guided condition passes every assertion is stronger; one repetition remains provisional until repeated.
* `=` — historical or explicitly provisional tie where both conditions passed without discrimination; it is not evidence of skill efficacy.
* `?` — protocol-valid but non-discriminating or inconclusive measurement; revise the benchmark before judging the skill. This is not evidence that the skill failed.
* `⚠` — a protocol-valid, discriminating negative result where the baseline outperformed the skill; see the linked report.
* `–` — not yet tested on that model/harness.

For quota-aware screening, a fixed lower-cost model/effort may execute the
complete five-case pack with independent pairs running concurrently after
filesystem containment is verified. Record that run in its own model/effort
column; do not mix it with a stronger-model run or treat a one-repetition
screen as statistical evidence.

* Links point to the sanitized report (`results/*.md` — human-readable) and the machine-readable result file (`results/*.json` — validated by `scripts/validate_repository.py`).

| Skill | `gpt-5.6-luna` / Codex (`low`) | `gpt-5.6-sol` / Codex (`xhigh`) | `muse-spark-1.2-contributor` / `muse code` (`xhigh`, `0.1.0`) | `tencent/hy3:free` / `Kilo` (`default`) | `gpt-5.6-luna` / Codex (`max`) |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `agent-guidance-maintenance` | [✓](2026-08-10-catalog-expansion.md) | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `ai-slop-detector` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `architecture-review` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `bootstrap-project` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `code-review` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | [?](results/2026-08-13-controls-gpt-5.6-luna-codex-max.md) · [machine](results/2026-08-13-controls-gpt-5.6-luna-codex-max.json) |
| `documentation-review` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `frontend-quality-review` | – | – | – | – | [?](results/2026-08-13-frontend-quality-review-gpt-5.6-luna-codex-max-pilot.md) · [machine](results/2026-08-13-frontend-quality-review-gpt-5.6-luna-codex-max-pilot.json) |
| `harness-adaptation` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `parallel-multi-agent` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `quality-hardening` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `reduce-code-size` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `rules-and-skills-audit` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `security-review` | [✓](2026-08-10-catalog-expansion.md) | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | [?](results/2026-08-13-controls-gpt-5.6-luna-codex-max.md) · [machine](results/2026-08-13-controls-gpt-5.6-luna-codex-max.json) |
| `skill-authoring` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `skill-evaluation` | [✓](2026-08-10-catalog-expansion.md) | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `skill-optimizer` | – | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `catalog-discovery` | – | – | [✓](results/2026-08-12-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-12-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `git-github-workflow` | – | – | [✓](results/2026-08-12-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-12-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `skill-reviewer` | [✓](2026-08-10-external-skill-intake.md) (`fab98c2`) | – | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `systematic-debugging` | [=](2026-08-10-catalog-expansion.md) / [✓](2026-08-11-systematic-debugging-fixture.md)† | [=](2026-08-11-systematic-debugging-fixture.md)† | [✓](results/2026-08-11-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-11-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `threat-modeling` | – | – | – | – | – |
| `upstream-contribution` | – | – | [✓](results/2026-08-12-muse-spark-1.2-contributor-muse-code.json) · [human](results/2026-08-12-muse-spark-1.2-contributor-muse-code.md) | [✓](results/2026-08-12-tencent-hy3-free-kilo.json) · [human](results/2026-08-12-tencent-hy3-free-kilo.md) | – |
| `adversarial-pr-review` | – | – | [✓](results/2026-08-12-muse-spark-1.2-contributor-muse-code-eval-rerun-3.json) · [human](results/2026-08-12-muse-spark-1.2-contributor-muse-code-eval-rerun-3.md) | – | – |
| `dependency-upgrade` | – | – | [✓](results/2026-08-12-muse-spark-1.2-contributor-muse-code-eval-rerun-3.json) · [human](results/2026-08-12-muse-spark-1.2-contributor-muse-code-eval-rerun-3.md) | – | – |

## Additional model-specific screening

| Skill | `gpt-5.4-mini` / Codex CLI (`high`) |
| :--- | :--- |
| `ai-slop-detector` | [✓](results/2026-08-13-ai-slop-detector-gpt-5.4-mini-codex-high-contained.json) · [human](results/2026-08-13-ai-slop-detector-gpt-5.4-mini-codex-high-contained.md) |
| `frontend-quality-review` | [?](results/2026-08-13-frontend-quality-review-gpt-5.4-mini-codex-high-contained.json) · [human](results/2026-08-13-frontend-quality-review-gpt-5.4-mini-codex-high-contained.md) |

† `systematic-debugging` fixture evaluation (order-recovery) passed 4/4 in both conditions for `luna` and `sol` on Codex — no discriminating advantage, decision `KEEP_PROVISIONAL`. See [2026-08-11-systematic-debugging-fixture.md](2026-08-11-systematic-debugging-fixture.md).

## How to read the matrix

* Every new `✓`, `=`, `?`, or `⚠` must correspond to a result file under `docs/evaluations/results/` with the independent-worker evidence required by [`skill-evaluation`](../../.agents/skills/skill-evaluation/SKILL.md), in addition to `schema_version`, `harness`, `model`, `baseline`, per-case `skill_pass`/`baseline_pass`/`better`, and `decision`. The repository validator checks the structural fields; the run record must separately document the worker/session boundary. Historical files are structurally validated but are not proof of this stronger protocol by themselves.
* `–` does not mean the skill is broken — it means that model/harness combination has not yet been measured. Add a run to fill the column.

## How to add a run

The human interface is conversation only — ask the agent to follow `skill-evaluation`; the agent executes all steps and the human does not need to run scripts manually.

1. Agent follows `skill-evaluation` to launch a fresh `WITH-SKILL` subagent/session and a different fresh `BASELINE` subagent/session for each `evals/evals.json` case and repetition, with separate per-condition workspaces containing only the same `evals/files/*` snapshot. The worker roots must also be filesystem-contained so parent traversal cannot reveal sibling evaluation roots, catalog/worktree content, memory, or parent-only traces. A role-played baseline is invalid.
2. Agent grades each `assertions` entry with quoted evidence, performs human review, and records timing/tokens if available.
3. Agent adds a result file `docs/evaluations/results/YYYY-MM-DD-<model>-<harness>.json` (or `<skill>-<model>-<harness>.json` for single-skill runs) conforming to the schema in `docs/evaluations/results/README.md`.
4. Agent updates this matrix: change `–` to `✓`, `=`, `?`, or `⚠` as justified by the result and link to the new result file and any sanitized report.
5. Agent regenerates `SUMMARY.md` with `python3 scripts/generate_evaluation_summary.py --write`.
6. Agent runs `make check` — the evaluation-result validator verifies the JSON shape, `skill_name` matches an existing skill, `model`/`harness` are recorded, linked files exist, and `SUMMARY.md` is fresh.

## Current coverage

* `24` skills have `evals/evals.json` definitions; `23` have executed results so far (the remaining newly added skill remains `–` until a clean-context run is recorded).
* Historical runs: `2026-08-10` (`gpt-5.6-luna` low, 4 skills), `2026-08-10` external intake (`gpt-5.6-luna` low, `skill-reviewer`), `2026-08-11` fixture (`gpt-5.6-luna` low + `gpt-5.6-sol` xhigh, `systematic-debugging`), `2026-08-11` (`muse-spark-1.2-contributor` `xhigh` / `muse code` 0.1.0, 17 skills), `2026-08-12` (`muse-spark-1.2-contributor` `xhigh` / `muse code` 0.1.0, 3 skills).
* Latest historical runs `2026-08-11-muse-spark-1.2-contributor-muse-code.json` (17 skills), `2026-08-12-muse-spark-1.2-contributor-muse-code.json` (3 skills), and `2026-08-12-muse-spark-1.2-contributor-muse-code-eval-rerun-3.json` (2 skills) record all 22 previously evaluated skills as outperforming baseline on their assertion sets. A full historical `Kilo` / `tencent/hy3:free` run records the same for 20 skills. These files document isolated workspaces but do not, from committed metadata alone, prove that the two conditions used different fresh workers; treat them as provisional and rerun under the independent-worker protocol before relying on the claims. One run per condition per model is not a statistical benchmark; effort level (`low` vs `xhigh`) can change results dramatically.
* The 2026-08-13 `gpt-5.6-luna` / Codex CLI (`max`) full canaries were protocol-valid but non-discriminating: `frontend-quality-review` scored 6/9 vs 6/9; the diagnostic controls scored `code-review` 11/13 vs 11/13 and `security-review` 9/11 vs 9/11. They are marked `?`; no skill efficacy decision is claimed. A subsequent frontend pilot using the first revised matching case scored 5/5 vs 4/5, but remains `?` because the other four cases and repetitions are not yet run.
* The 2026-08-13 `gpt-5.4-mini` / Codex CLI (`high`) `ai-slop-detector` full pack was protocol-valid and modestly discriminating: 25/30 vs 24/30, with the guided condition passing the post-cleanup verification assertion that the baseline missed. It is marked `✓` under `KEEP_PROVISIONAL`; the one-repetition margin is not universal or statistical evidence.
