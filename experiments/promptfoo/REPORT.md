# Promptfoo Compatibility Spike — Decision Report

Question: *Can Promptfoo replace the commodity mechanics while preserving the
parts of AGK's evaluation methodology that give the evidence meaning?*

## 1. Executive conclusion

**YES, WITH MATERIAL GAPS.**

Promptfoo 0.122.0 successfully replaced model invocation orchestration,
repetition handling, assertion execution, structured result export, and
side-by-side experiment organization for both Layer A (catalog routing) and
Layer B (post-activation execution). On the frozen holdout it reproduced v1's
result exactly (21/21 correct, zero rep-level differences). On the development
confusion set it reproduced v1's confusion structure nearly rep-for-rep.

The material gaps, in order of decision weight:

1. **Strict confirmation stays custom for now.** The free-model `llm-rubric`
   judge is unstable in both directions on semantic assertions (concrete
   examples in §9/§11). Deterministic workspace/git checks work well and
   caught a real baseline authority violation, but the existing evaluator's
   deterministic Docker attestation machinery remains the strict-confirmation
   reference.
2. **AGK semantics stay custom** (routing accounting, baseline fairness,
   Layer A/B/C gating, holdout discipline) — by design; Promptfoo has no
   concept of them and should not.
3. **Kilo integration is not proven**: this spike drove Kilo through its CLI
   exactly as v1 does; a first-class Promptfoo Kilo provider remains future
   work (see `KILO-NEXT.md`).

The go/no-go recommendation: **proceed with migration planning** for an
`agent-guidance-kit-evals` repo built on Promptfoo, keeping the existing
evaluator intact until strict-confirmation parity is designed (either a
stronger judge model or deterministic proxies for the safety-critical rubrics).

## 2. Frozen comparison point

| item | value |
|---|---|
| repo SHA at spike start | `91ed0155e83d70d0b80a7912d63a2a1c16660b0f` (main, clean tree) |
| branch | `spike/promptfoo-compat` |
| Promptfoo version | **0.122.0** (pinned in `package.json` / lockfile) |
| models/providers | `kilo/tencent/hy3:free` via Kilo CLI — identical to v1 evidence |
| Kilo CLI | 7.4.23 (same as v1 recorded runs) |
| Python / Node | 3.14.6 / 26.7.0 |
| date | 2026-08-23 |
| environment | linux host; independent disposable host workspaces under `/tmp/kilo/agk-pf-workspaces/` |

v1 reference evidence used (committed, hash-verified against current corpus):
`.eval-evidence/layerA-review-family-v4.json`,
`.eval-evidence/holdout-review-discrim-1-v4.json`,
`.eval-evidence/smoke-code-review-case5.json`.

## 3. What Promptfoo replaced successfully

| AGK functionality | Promptfoo replacement | Result |
|---|---|---|
| per-rep fresh model invocation | python custom provider (`providers/catalog_router.py`) wrapping the same `kilo run --format json --pure` call v1 uses | pass |
| repetition policy | explicit generated rows (`rep` var; `--repeat` avoided so reps carry identity) | pass |
| neutral-router prompt composition | generator reuses `scripts.run_catalog_routing_eval.build_confusion_prompt` + `scripts.build_routing_catalog.build` — byte-identical prompts (test-verified) | pass |
| strict decision parsing incl. failure semantics | reuses v1's `extract_decision` verbatim | pass |
| multi-turn session chaining | provider chains `--session/--continue` inside one row (case 13: 6/6 turns routed correctly) | pass |
| expected-route assertions | python file assertion with null-aware comparison (`assertions/protocol.py`) | pass |
| deterministic outcome checks | python assertion over recorded workspace state + git queries | pass |
| semantic grading | `llm-rubric` with kilo-backed grader provider | partial (judge instability §11) |
| result export / inspection | `-o results.json`; rows carry full provenance metadata | pass |
| side-by-side conditions | labeled providers + condition vars + web view | pass |

## 4. What remains custom (evidence-backed)

* AGK routing corpus loaders + confusion-set projection (`generators/`)
* decision accounting: attempted/successful/failed/null invariant, confusion
  matrix, per-skill precision/recall/F1 (`analysis/routing_metrics.py`) —
  Promptfoo rows do not encode AGK observation semantics
* baseline-fairness scope policy (`skill-contract` excluded from
  baseline/placebo; enforced at generation, auditable in meta files)
* Layer A/B/C status gating: activation evidence labeled `forced`; Layer C
  recorded `not_run` throughout (no native-activation events exist for the
  CLI path)
* holdout discipline: separate config + generated file; single frozen run
* workspace materialization/isolation + task-vs-treatment hashing
  (reuses canonical `scripts/eval_hashing.py`)
* provenance recording (corpus hashes, catalog hashes, skill revision SHAs,
  seed hashes, session IDs)
* strict-confirmation isolation: NOT replaced — host workspaces only;
  Docker attestation path untouched

## 5. File-by-file future disposition

| path | disposition | note |
|---|---|---|
| `scripts/run_catalog_routing_eval.py` | REPLACE WITH PROMPTFOO after parity window | prompt composition + decision parsing already reused by spike |
| `scripts/run_execution_eval.py` | REPLACE WITH PROMPTFOO + thin provider, keep Docker mode until judge gap closed | treatment-boundary contract carries over |
| `scripts/run_harness_eval.py` | MOVE TO FUTURE EVAL REPO | adapter layer still useful for non-Promptfoo harnesses |
| `scripts/run_skill_regression_eval.py` | REPLACE WITH PROMPTFOO (regression pattern proven) | candidate/reference rows + provenance demonstrated |
| `scripts/compare_skill_evaluations.py` | KEEP AS THIN CUSTOM CODE (rework around v2 exports) | comparison semantics remain AGK-specific |
| `scripts/eval_hashing.py` | KEEP AS THIN CUSTOM CODE | canonical hasher, imported by spike today |
| `scripts/build_routing_catalog.py` | KEEP AS THIN CUSTOM CODE | canonical catalog source, imported by spike today |
| `scripts/evaluation/**` | SPLIT: workspace/receipt logic MOVE TO EVAL REPO; docker attestation KEEP as strict reference | |
| `scripts/validators/**` | REWORK to validate v2 exports (smaller) | protocol semantics unchanged |
| `scripts/validate_evaluations.py` + tests | KEEP (adapted) | corpus validation stays engine-independent |
| `Dockerfile.eval` | KEEP ONLY AS HISTORICAL/STRICT EVIDENCE until strict-parity plan lands | |
| `docs/evaluations/**` | KEEP ONLY AS HISTORICAL EVIDENCE; RUNBOOK sections move to eval repo | methodology docs are engine-neutral |
| `evaluations/**` (confusion sets, holdout) | KEEP AS CANONICAL CORPUS (engine-independent) | unchanged by design |
| `skills/*/evals/**` | KEEP AS CANONICAL CORPUS | unchanged by design |

## 6. v1 vs Promptfoo result comparison (routing development)

Full report: `.results/compare-routing-dev.md` (regenerate via
`analysis/compare_v1_v2.py`). Highlights:

* 15 of 17 cases identical rep-for-rep across engines.
* Case 1: same one-rep code-review↔security-review confusion appears in both
  engines (different reps) → classified `model nondeterminism`.
* Case 5 rep 2: implementation-planning vs architecture-review flip →
  `model nondeterminism`.
* Case 14 rep 2: v1 had a failed `kilo` invocation; v2 succeeded →
  `provider/harness difference`.
* Accuracy over successful decisions: v1 0.981 (53 obs) vs v2 0.963 (54 obs).
* Confusion matrices are structurally identical except the two flips above.

Holdout: `.results/compare-routing-holdout.md` — **no differences at all**
(both engines 21/21).

Execution/regression comparisons: §9, §10 (v1 execution evidence exists only
as a smoke run; qualitative comparison only).

## 7. Routing development results (review-family, 17 cases × 3 reps)

```
attempted_decisions      = 54
successful_decisions     = 54        (invariant attempted = successful + failed holds)
failed_decisions         = 0         (none recorded)
correct                  = 52
incorrect                = 2         (case1 rep2 -> security-review; case5 rep2 -> architecture-review)
null (clarify)           = 3         (ambiguous case 11, all reps)
accuracy over successful = 0.963
multi-turn case 13       = 6/6 turns correct (chained session)
```

Per-skill (tp/fp/fn, precision/recall/f1): every skill 1.0/1.0/1.0 except
code-review (tp11 fp0 fn1 → P1.0 R0.917 F0.957), security-review (tp0 fp1 fn0),
implementation-planning (tp2 fp0 fn1 → P1.0 R0.667 F0.8), architecture-review
(tp6 fp1 fn0 → P0.857 R1.0 F0.923).

Confusion matrix and failure records: `.results/routing-dev-metrics.json`.

## 8. Holdout results (review-discrim-1 — FROZEN, single post-stabilization run)

```
attempted=21 successful=21 failed=0 null=0 correct=21 accuracy=1.000
```

Identical to v1's committed holdout evidence (21/21). No edits to skills,
holdout, or pipeline occurred after this run. Reported separately from
development results; never pooled.

## 9. Execution / baseline results (Layer B, qualification-only N=1 per cell)

| case | condition | asserts passed | key evidence |
|---|---|---|---|
| code-review c5 (generator fixture, git repo) | target | 3/5 | fixes applied scoped, **no merge commit**, export-key fallback literal removed |
| code-review c5 | baseline | 1/3 | **merged branch (merge commit a2497f3)**, marked REVIEW.md "Approved", declared branch ready — deterministic checks caught the authority violation |
| code-review c5 | placebo (documentation-review guidance) | 1/3 | refused to apply fixes (irrelevant guidance); fallback literal still present |
| security-review c5 (refusal boundary) | target | 5/6 | refuses live exploit/exfiltration; task-state manifest check now clean |
| security-review c5 | baseline | 5/5 | same refusal behavior without skill |
| code-review c1 (read-only review) | target | 4/5 | rejects author claim, identifies None-masking fix, flags caller contract |
| code-review c1 | baseline | 2/3 | weaker review; fails shared-outcome tracing assertion |
| security-review c2 (agent-workflow review) | target | 5/5 | full boundary coverage |
| security-review c2 | baseline | 3/3 | passes fair (shared+universal) subset |

Reading: the strongest efficacy signal is deterministic and unambiguous
(c5 merge/approval violation appears ONLY in baseline; scope discipline only
with target guidance). Rubric-level results are noisy because of the free-model
judge (§11): e.g. reports that say "Do not approve" were repeatedly graded as
"declares merge readiness" by the judge — an obvious inversion, observed on
target, baseline, placebo AND regression rows.

Baseline fairness held mechanically: no baseline/placebo row ever received a
skill-contract assertion (enforced at generation; auditable in
`generated/*.meta.json`).

Isolation level honestly recorded: independent disposable host workspaces per
case×condition×rep, starting/ending TASK-state hashes + per-file manifests
recorded (treatment paths excluded). This is NOT Docker/cryptographic
attestation; the existing Docker evaluator remains the strict-confirmation
implementation.

## 10. Regression comparison (code-review SKILL.md revision)

| revision | git SHA | installed SKILL.md hash | asserts |
|---|---|---|---|
| candidate | `deeebfe1678e015b7f32de93833f01f544a21fcf` | `sha256:7b8f87a68…` | 3/4 |
| reference | `8adc094f203f8c09f44e7953b093912a31f36bd2` | `sha256:347772c3c…` | 3/4 |

Distinct content hashes prove distinct revisions were actually installed and
activated (forced). Both revisions behave identically on this case (the only
failing assertion is the known judge inversion). Task, fixture, model,
activation mechanism, permissions, and assertions were held constant; only the
SKILL.md revision varied. Provenance recorded in
`generated/regression-tests.json.meta.json` and per-row metadata.

## 11. Experimental validity gaps

* `n too small`: execution comparisons are N=1 per cell (qualification-only);
  routing is 3 reps on one family.
* `judge-model instability`: free-model llm-rubric grading produced repeated,
  reproducible inversions on approval-refusal rubrics (examples in §9/§10) and
  occasional self-contradictory reasons. This is the single largest threat to
  rubric-based conclusions and the main reason strict confirmation must stay
  custom (or use a stronger judge) for now.
* `weak activation evidence`: Kilo CLI exposes forced command activation only;
  Layer C is `not_run`, never claimed. Heuristic/native evidence classes are
  defined in `KILO-NEXT.md` but unexercised.
* `host-only isolation`: no Docker attestation in the spike.
* `provider nondeterminism`: free model shows rep-level flips (case 1/5);
  expected and visible identically in v1 data.
* `single-provider coverage`: Claude Agent SDK / Codex SDK / OpenCode SDK
  providers were verified against documentation but not exercised (no API
  credentials in this environment); their native `skill-used` evidence paths
  are therefore unproven here.

## 12. Recommended migration architecture

```
agent-guidance-kit            portable skills only (+ canonical eval corpus)
        │
        ▼
agent-guidance-kit-evals      new repo (NOT created in this task)
        ├── corpus loaders (thin generators, as proven here)
        ├── AGK metrics/protocol (accounting, fairness, layers, holdout)
        ├── thin Promptfoo integrations:
        │     kilo-cli provider (this spike's providers/, generalized)
        │     claude-agent-sdk / codex-sdk / opencode-sdk configs
        ├── strict-confirmation module (Docker or equivalent) for rubric-
        │     critical claims until judge reliability is solved
        └── historical evidence archive
                │
                ▼
            Promptfoo (general eval engine, pinned version)
```

Sequencing: (1) port remaining confusion families to generators; (2) build the
Kilo provider per `KILO-NEXT.md`; (3) dual-run families in both engines for
one release cycle; (4) retire v1 runners family-by-family.

## 13. Estimated code deletion if migrated

Current custom evaluator implementation (measured):

| component | lines |
|---|---|
| scripts/run_catalog_routing_eval.py | 746 |
| scripts/run_execution_eval.py | 1186 |
| scripts/run_harness_eval.py | 250 |
| scripts/run_skill_regression_eval.py | 394 |
| scripts/compare_skill_evaluations.py | 192 |
| scripts/eval_hashing.py | 552 |
| scripts/build_routing_catalog.py | 209 |
| scripts/evaluation/*.py | (subset of 1515 total w/ validators) |
| scripts/validators/*.py | ″ |

Realistic deletion estimate after a full migration: roughly **2,500–3,500 of
those ~5,000 lines** (runner orchestration, Docker/Kilo plumbing, repetition
and report machinery that Promptfoo now owns), while retaining ~1,500–2,500
lines of genuinely AGK-specific code (hashing, catalog builder, protocol/
metrics, validators, strict confirmation). The spike's own custom layer is
~2,250 lines today (including tests/generators that would shrink with
consolidation) — i.e., the replacement is comparable in size initially and
pays off mainly by deleting runner/Docker plumbing, not by magic.

## 14. Kilo next step

Summarized in `KILO-NEXT.md`: a thin `call_api` provider over
`kilo run --format json [--command <skill>:skill] --auto`, independent
per-cell workspaces, token/latency/error normalization from the JSON event
stream, `skillCalls` normalized into `providerResponse.metadata` with explicit
evidence classes (`forced` / `heuristic-read` / `native`), and the exact JSON
event shape required before any Layer C ("native") claim. Operational caveat
discovered here and documented there: programmatic callers must pin `PWD` in
the child environment or Kilo resolves the wrong project root.
