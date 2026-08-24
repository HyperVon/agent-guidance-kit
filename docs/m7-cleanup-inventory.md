# M7 Cleanup Inventory

This is the pre-deletion inventory for M7, based on AGK `origin/main` at
`2542ed76b58ed254ecbe986a259cc28c5344a50c` and the eval-repository M4/M6
ownership records. It is a migration record, not an evaluation procedure.

## Disposition Rules

| Disposition | Meaning in this inventory |
| --- | --- |
| `DELETE` | Evaluator implementation, corpus, evidence, or framework-owned content removed from AGK. |
| `RETAIN` | Portable product content or migration history still needed through M8. |
| `REWRITE` | Mixed product/contributor content updated to remove evaluator operation. |
| `REPLACE-WITH-STATIC` | Evaluator validation replaced by a small skill-library integrity check. |
| `HISTORICAL-POINTER` | A small pointer remains without duplicating evaluator data or procedures. |

## Canonical Corpus

| AGK path | Disposition | Reason and canonical responsibility |
| --- | --- | --- |
| `evaluations/**` (5 files) | `DELETE` | Confusion sets and protected holdout are canonical under `agent-guidance-kit-evals/corpus/`; M4 manifest and holdout hash provide ownership/provenance. |
| `skills/*/evals/**` (140 files, 26 packs) | `DELETE` | Per-skill corpus is canonical under `agent-guidance-kit-evals/corpus/skills/`; M4 manifest records exact-copy parity. |
| `Dockerfile.eval` | `DELETE` | Evaluator isolation infrastructure belongs to the eval repository; M6 deferred strict confirmation there. |

## Evaluator Implementation

| AGK path | Disposition | Reason and canonical responsibility |
| --- | --- | --- |
| `scripts/evaluation/**` (7 modules) | `DELETE` | Evaluator workspace, receipts, attestation, harness, and regression implementation moved to the eval repository. |
| `scripts/validators/**` (7 modules) | `DELETE` | Evaluation result/protocol validators moved to the eval repository. |
| `scripts/build_routing_catalog.py` | `DELETE` | Routing experiment/catalog generation is eval-owned. |
| `scripts/compare_skill_evaluations.py` | `DELETE` | Evaluation result comparison is eval-owned. |
| `scripts/docker_isolation_preflight.py` | `DELETE` | Docker evaluator preflight is eval-owned. |
| `scripts/eval_hashing.py` | `DELETE` | Evaluation fixture/result/provenance hashing is eval-owned. |
| `scripts/evaluation_harness.py` | `DELETE` | Evaluator harness orchestration is eval-owned. |
| `scripts/evaluation_protocols.py` | `DELETE` | Evaluation protocol definitions are eval-owned. |
| `scripts/hash_fixtures.py` | `DELETE` | Evaluation fixture hashing is eval-owned. |
| `scripts/run_catalog_routing_eval.py` | `DELETE` | Routing execution is eval-owned. |
| `scripts/run_execution_eval.py` | `DELETE` | Target/baseline execution is eval-owned. |
| `scripts/run_harness_eval.py` | `DELETE` | Harness evaluation is eval-owned. |
| `scripts/run_skill_regression_eval.py` | `DELETE` | Revision comparison execution is eval-owned. |
| `scripts/validate_evaluations.py` | `DELETE` | Evaluator corpus/result validation is eval-owned. |
| `scripts/test_validate_evaluations.py` | `DELETE` | Tests for removed evaluator validation are removed with it. |
| `scripts/` | `REPLACE-WITH-STATIC` | Add only the product-static catalog/frontmatter/link validator and its standard-library tests. |

## Framework-Bound Skill

| AGK path | Disposition | Reason and canonical responsibility |
| --- | --- | --- |
| `skills/skill-evaluation/**` (3 files) | `DELETE` | Framework-bound evaluator skill no longer belongs in a portable skill library; no replacement is authored in M7. |

## Evaluation History and Documentation

| AGK path | Disposition | Reason and canonical responsibility |
| --- | --- | --- |
| `docs/evaluations/RUNBOOK.md` | `DELETE` | Operational evaluator runbook is now eval-repo-owned. |
| `docs/evaluations/SUMMARY.md` | `DELETE` | Historical evaluator summary is preserved under eval-repo `historical-v1/`. |
| `docs/evaluations/validation-matrix.md` | `DELETE` | Historical evaluator matrix is preserved under eval-repo `historical-v1/`. |
| `docs/evaluations/frontmatter-bloat-inventory.md` | `DELETE` | Historical evaluator inventory is preserved under eval-repo `historical-v1/`. |
| `docs/evaluations/phase1-environment.md` | `DELETE` | Historical evaluator environment record is preserved under eval-repo `historical-v1/`. |
| `docs/evaluations/harness-adapter.md` | `DELETE` | Evaluator adapter methodology is preserved under eval-repo `historical-v1/`. |
| `docs/evaluations/protocol-spec.md` | `DELETE` | Evaluator protocol history is preserved under eval-repo `historical-v1/`. |
| `docs/evaluations/result-schema.md` | `DELETE` | Evaluator schema history is preserved under eval-repo `historical-v1/`. |
| `docs/evaluations/routing-experiments.md` | `DELETE` | Routing experiment methodology is eval-owned. |
| `docs/evaluations/results/**` (11 files) | `DELETE` | Historical v1 result records are preserved under eval-repo `historical-v1/results/`. |
| `docs/evaluations/promptfoo-spike/M1-REPORT.md` | `DELETE` | Durable report-only M1 evidence is preserved under eval-repo `historical-m1-promptfoo/`; AGK keeps only a pointer. |
| `docs/evaluations/promptfoo-spike/KILO-NEXT.md` | `DELETE` | Superseded provider design note is represented by eval-repo M5/M6 integration records. |
| `docs/evaluations/promptfoo-spike/M2-REVIEW.md` | `DELETE` | Decision history is represented by ADR-0001 and the milestone tracker. |
| `docs/evaluations/promptfoo-spike/evidence-manifest.json` | `DELETE` | M1 retention metadata is superseded by eval-repo provenance; raw exports were never durable. |
| `docs/evaluations/promptfoo-spike/sanitized-*` and metrics | `DELETE` | Non-authoritative spike representations are not canonical evidence; the eval repo retains the report-only durable record and M6 interpretation. |
| `docs/evaluations/promptfoo-spike/README.md` | `HISTORICAL-POINTER` | Replace the old spike directory index with a pointer to eval-repo historical evidence. |
| `docs/evaluations/evidence-evaluator-architecture.md` | `RETAIN` | Historical architecture/migration record required through M8; mark current evaluator operation as eval-repo-owned. |
| `docs/evaluations/evidence-evaluator-milestones.md` | `RETAIN` | Active M0–M8 migration tracker; update M7 completion only after validation. |
| `docs/adr/0001-promptfoo-backed-evaluator.md` | `RETAIN` | Accepted historical architecture decision; repair evidence links to stable eval-repo paths. |

## Product and CI Surface

| AGK path | Disposition | Reason |
| --- | --- | --- |
| `README.md` | `REWRITE` | Make browse → review → select → copy/adapt the complete primary adoption path. |
| `AGENTS.md` | `REWRITE` | Retain skill/contribution/review policy; remove active evaluator methodology and commands. |
| `.github/workflows/check.yml` | `REWRITE` | Replace evaluator CI with static catalog/frontmatter/link checks and remaining helper lint/tests. |
| `.github/workflows/codeql.yml` | `DELETE` | Final executable surface is a small static validator; CodeQL no longer provides proportional value. |
| `.github/codeql/codeql-config.yml` | `DELETE` | Only supported evaluator exclusions; no longer needed after CodeQL removal. |
| `pyproject.toml` | `REWRITE` | Retain only minimal Ruff configuration for the small static validator. |
| `.gitignore` | `REWRITE` | Remove evaluator result, Docker workspace, and evaluation workspace patterns. |

## Ownership Verification

Before deletion, the eval repository records:

- `skills/<skill>/evals/**` → `corpus/skills/<skill>/evals/**`;
- `evaluations/confusion-sets/**` → `corpus/confusion-sets/**`;
- `evaluations/holdout/review-discrim-1.json` → protected
  `corpus/holdout/review-discrim-1.json`;
- historical v1 result/docs → `historical-v1/**`;
- report-only M1 evidence → `historical-m1-promptfoo/M1-REPORT.md`;
- protected holdout SHA-256:
  `e2ad6dac06d64f8efad17df96d6c6f3af13c7f3a88aac25b19fe87587936dd35`.

The M1 sanitized exports are explicitly non-authoritative representations, and
the raw exports were never committed. No unique canonical corpus or durable raw
evidence is deleted by this inventory.
