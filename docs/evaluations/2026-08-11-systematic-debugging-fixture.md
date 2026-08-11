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
- Scored model conditions: `gpt-5.6-luna` at low reasoning effort and
  `gpt-5.6-sol` at xhigh reasoning effort, with one run per condition for each
  model.
- Raw outputs were not committed. Pi 0.80.3 was installed locally, but its
  noninteractive runner had no configured model, so no Pi result is claimed.

## Results

All four committed matching-case assertions passed in both conditions for both
scored models. A candidate fifth assertion was tested and rejected during
review because it
conflicted with the fixture: the scenario explicitly defines unspecified
states as `RELEASE`, so preserving that behavior is correct unless additional
evidence changes the contract.

| Model / condition | Assertions | Human review |
| :--- | :--- | :--- |
| Luna low / no skill | 4/4 | Found the explicit `UNCERTAIN` bug, rejected a blind retry, and preserved the fixture's specified mappings. |
| Luna low / `systematic-debugging` | 4/4 | Found the same root cause, rejected a blind retry, and preserved the fixture's specified mappings. |
| Sol xhigh / no skill | 4/4 | Found the explicit `UNCERTAIN` bug, rejected a blind retry, and preserved the fixture's specified mappings. |
| Sol xhigh / `systematic-debugging` | 4/4 | Found the same root cause, rejected a blind retry, and more explicitly bounded the identity-related uncertainty. |

The rejected candidate assertion was:

> The response does not recommend preserving catch-all `RELEASE` behavior for
> unspecified states as expected behavior.

That assertion would reward contradicting the fixture rather than applying the
skill. It is not part of the committed case set.

## Decision and limits

`KEEP_PROVISIONAL`: the fixture confirms that the skill preserves the safety
boundary across two Codex model conditions, but the comparisons found no
assertion-level advantage over the no-skill baseline. It is smoke-level
evidence from two models and one run per condition for each model, and does not
establish model-independent or harness-wide behavior. Repeat the case across
additional supported models and harnesses before making portability or
statistical claims.
