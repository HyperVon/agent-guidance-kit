# Systematic debugging fixture evaluation — 2026-08-11

## Scope and method

This follow-up evaluated `systematic-debugging` with the committed order-
recovery fixture. The fixture contains a recovery function, a persistence
contract, and a failing test where an `UNCERTAIN` order incorrectly becomes
`RELEASE` instead of `HOLD`.

- Baseline: the same scenario and fixture content without the skill.
- Revised condition: the same scenario and fixture content plus the complete
  `systematic-debugging` skill.
- Harness: ephemeral local Codex execution with read-only sandboxing, project
  rules disabled, and tool use prohibited by the evaluation prompt.
- Model: `gpt-5.6-luna`, low reasoning effort.
- One run per condition; raw outputs were not committed.

## Results

All four committed matching-case assertions passed in both conditions. A
candidate fifth assertion was tested and rejected during review because it
conflicted with the fixture: the scenario explicitly defines unspecified
states as `RELEASE`, so preserving that behavior is correct unless additional
evidence changes the contract.

| Condition | Assertions | Human review |
| :--- | :--- | :--- |
| No skill | 4/4 | Found the explicit `UNCERTAIN` bug, rejected a blind retry, and preserved the fixture's specified mappings. |
| `systematic-debugging` | 4/4 | Found the same root cause, rejected a blind retry, and preserved the fixture's specified mappings. |

The rejected candidate assertion was:

> The response does not recommend preserving catch-all `RELEASE` behavior for
> unspecified states as expected behavior.

That assertion would reward contradicting the fixture rather than applying the
skill. It is not part of the committed case set.

## Decision and limits

`KEEP_PROVISIONAL`: the fixture confirms that the skill preserves the safety
boundary and does not regress the matching case, but this comparison found no
text-level advantage over the no-skill baseline. It is smoke-level evidence
from one model and one run per condition, and does not establish
model-independent or harness-wide behavior. Repeat the case across additional
supported models and harnesses before making portability or statistical
claims.
