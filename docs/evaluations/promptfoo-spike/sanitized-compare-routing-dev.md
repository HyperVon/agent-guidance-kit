# v1 vs Promptfoo comparison — routing development (review-family)

## Provenance
- v1 evidence: `layerA-review-family-v4.json` (case_set_hash sha256:5e4dfe782126..., model kilo/tencent/hy3:free, kilo 7.4.23, reps 3)
- v2 export: `.results/routing-dev.json` (engine promptfoo 0.122.0, provider kilo-cli, same model family as v1)
- corpus: `../../evaluations/confusion-sets/review-family.json` (canonical hash sha256:5e4dfe782126...)
- v1 case_set_hash matches current corpus: **True**

## Accounting
| metric | v1 | v2 (promptfoo) |
|---|---|---|
| attempted | 54 | 54 |
| successful | 53 | 54 |
| failed | 1 | 0 |
| null selections | 3 | 3 |
| accuracy over successful | 0.981 | 0.963 |

## Per-case routes (rep-level)
| case | expected | v1 selections | v2 selections | diff? |
|---|---|---|---|---|
| 1 | code-review | code-review; code-review; security-review | code-review; security-review; code-review | same |
| 2 | threat-modeling | threat-modeling; threat-modeling; threat-modeling | threat-modeling; threat-modeling; threat-modeling | same |
| 3 | review-feedback-resolution | review-feedback-resolution; review-feedback-resolution; review-feedback-resolution | review-feedback-resolution; review-feedback-resolution; review-feedback-resolution | same |
| 4 | architecture-review | architecture-review; architecture-review; architecture-review | architecture-review; architecture-review; architecture-review | same |
| 5 | implementation-planning | implementation-planning; implementation-planning; implementation-planning | implementation-planning; architecture-review; implementation-planning | DIFFERENT |
| 6 | adversarial-pr-review | adversarial-pr-review; adversarial-pr-review; adversarial-pr-review | adversarial-pr-review; adversarial-pr-review; adversarial-pr-review | same |
| 7 | frontend-quality-review | frontend-quality-review; frontend-quality-review; frontend-quality-review | frontend-quality-review; frontend-quality-review; frontend-quality-review | same |
| 8 | documentation-review | documentation-review; documentation-review; documentation-review | documentation-review; documentation-review; documentation-review | same |
| 9 | systematic-debugging | systematic-debugging; systematic-debugging; systematic-debugging | systematic-debugging; systematic-debugging; systematic-debugging | same |
| 10 | architecture-review | architecture-review; architecture-review; architecture-review | architecture-review; architecture-review; architecture-review | same |
| 11 | null | null; null; null | null; null; null | same |
| 12 | code-review | code-review; code-review; code-review | code-review; code-review; code-review | same |
| 13 | review-feedback-resolution | review-feedback-resolution; review-feedback-resolution; review-feedback-resolution; review-feedback-resolution; review-feedback-resolution; review-feedback-resolution | review-feedback-resolution; review-feedback-resolution; review-feedback-resolution; review-feedback-resolution; review-feedback-resolution; review-feedback-resolution | same |
| 14 | review-feedback-resolution | review-feedback-resolution; FAILED; review-feedback-resolution | review-feedback-resolution; review-feedback-resolution; review-feedback-resolution | DIFFERENT |
| 15 | documentation-review | documentation-review; documentation-review; documentation-review | documentation-review; documentation-review; documentation-review | same |
| 16 | code-review | code-review; code-review; code-review | code-review; code-review; code-review | same |
| 17 | code-review | code-review; code-review; code-review | code-review; code-review; code-review | same |

Cases with any rep-level selection difference: **2** — classified per-rep below.

## Rep-level difference classifications
- **model nondeterminism** (3):
  - case 1 rep 2 turn None: v1='code-review'/success vs v2='security-review'/success
  - case 1 rep 3 turn None: v1='security-review'/success vs v2='code-review'/success
  - case 5 rep 2 turn None: v1='implementation-planning'/success vs v2='architecture-review'/success
- **provider/harness difference** (1):
  - case 14 rep 2 turn None: v1=None/failed vs v2='review-feedback-resolution'/success

## Confusion behavior (successful decisions)
- v2 confusion matrix: `{"code-review": {"code-review": 11, "security-review": 1}, "threat-modeling": {"threat-modeling": 3}, "review-feedback-resolution": {"review-feedback-resolution": 12}, "architecture-review": {"architecture-review": 6}, "implementation-planning": {"implementation-planning": 2, "architecture-review": 1}, "adversarial-pr-review": {"adversarial-pr-review": 3}, "frontend-quality-review": {"frontend-quality-review": 3}, "documentation-review": {"documentation-review": 6}, "systematic-debugging": {"systematic-debugging": 3}, "null": {"null": 3}}`
- v1 confusion matrix: `{"code-review": {"code-review": 11, "security-review": 1}, "threat-modeling": {"threat-modeling": 3}, "review-feedback-resolution": {"review-feedback-resolution": 11}, "architecture-review": {"architecture-review": 6}, "implementation-planning": {"implementation-planning": 3}, "adversarial-pr-review": {"adversarial-pr-review": 3}, "frontend-quality-review": {"frontend-quality-review": 3}, "documentation-review": {"documentation-review": 6}, "systematic-debugging": {"systematic-debugging": 3}, "null": {"null": 3}}`

## Failure accounting
- invariant attempted == successful + failed holds in v2: **True**
- v1 failed: {'case_id': 14, 'rep': 2, 'turn': None, 'error': 'kilo exited 1'}
