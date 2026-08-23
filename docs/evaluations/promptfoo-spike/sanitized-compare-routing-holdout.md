# v1 vs Promptfoo comparison — routing HOLDOUT (review-discrim-1)

## Provenance
- v1 evidence: `holdout-review-discrim-1-v4.json` (case_set_hash sha256:8be9419fd3ef..., model kilo/tencent/hy3:free, kilo 7.4.23, reps 3)
- v2 export: `.results/routing-holdout.json` (engine promptfoo 0.122.0, provider kilo-cli, same model family as v1)
- corpus: `../../evaluations/holdout/review-discrim-1.json` (canonical hash sha256:8be9419fd3ef...)
- v1 case_set_hash matches current corpus: **True**

## Accounting
| metric | v1 | v2 (promptfoo) |
|---|---|---|
| attempted | 21 | 21 |
| successful | 21 | 21 |
| failed | 0 | 0 |
| null selections | 0 | 0 |
| accuracy over successful | 1.000 | 1.000 |

## Per-case routes (rep-level)
| case | expected | v1 selections | v2 selections | diff? |
|---|---|---|---|---|
| 1 | code-review | code-review; code-review; code-review | code-review; code-review; code-review | same |
| 2 | systematic-debugging | systematic-debugging; systematic-debugging; systematic-debugging | systematic-debugging; systematic-debugging; systematic-debugging | same |
| 3 | architecture-review | architecture-review; architecture-review; architecture-review | architecture-review; architecture-review; architecture-review | same |
| 4 | implementation-planning | implementation-planning; implementation-planning; implementation-planning | implementation-planning; implementation-planning; implementation-planning | same |
| 5 | security-review | security-review; security-review; security-review | security-review; security-review; security-review | same |
| 6 | quality-hardening | quality-hardening; quality-hardening; quality-hardening | quality-hardening; quality-hardening; quality-hardening | same |
| 7 | requirements-and-design | requirements-and-design; requirements-and-design; requirements-and-design | requirements-and-design; requirements-and-design; requirements-and-design | same |

Cases with any rep-level selection difference: **0** — classified per-rep below.

## Rep-level difference classifications
No rep-level status/selection differences detected.

## Confusion behavior (successful decisions)
- v2 confusion matrix: `{"code-review": {"code-review": 3}, "systematic-debugging": {"systematic-debugging": 3}, "architecture-review": {"architecture-review": 3}, "implementation-planning": {"implementation-planning": 3}, "security-review": {"security-review": 3}, "quality-hardening": {"quality-hardening": 3}, "requirements-and-design": {"requirements-and-design": 3}}`
- v1 confusion matrix: `{"code-review": {"code-review": 3}, "systematic-debugging": {"systematic-debugging": 3}, "architecture-review": {"architecture-review": 3}, "implementation-planning": {"implementation-planning": 3}, "security-review": {"security-review": 3}, "quality-hardening": {"quality-hardening": 3}, "requirements-and-design": {"requirements-and-design": 3}}`

## Failure accounting
- invariant attempted == successful + failed holds in v2: **True**
