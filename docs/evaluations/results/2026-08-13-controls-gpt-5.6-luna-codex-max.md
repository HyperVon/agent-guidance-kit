# Diagnostic control run — 2026-08-13 — `gpt-5.6-luna` / Codex CLI (`max`)

Human-readable companion to [`2026-08-13-controls-gpt-5.6-luna-codex-max.json`](2026-08-13-controls-gpt-5.6-luna-codex-max.json).

* **Run ID:** `2026-08-13-controls-gpt-5.6-luna-codex-max`
* **Timestamp:** `2026-08-13T10:58:15Z`
* **Harness:** Codex CLI `0.147.0-alpha.6.5`
* **Model:** `gpt-5.6-luna` (`provider: openai`, `reasoning_effort: max`)
* **Baseline:** `harness-default` (normal Codex context with the target skill omitted)

## Why these controls

The new frontend skill tied its fresh baseline at 6/9. To test whether that
result reflected weak skill content or weak assertions, this run used two
established review skills with the same corrected isolation protocol. Their
matching and edge cases received small, relevant source/contract/test
snapshots; the routing cases remained intentionally fixture-free.

## Protocol verification

This was a valid independent-worker comparison. Sixteen scored sessions were
used: two conditions for four cases in each of two skills, with the two
code-review fixture cases rerun after correcting an accidental malformed-patch
fixture. The initial malformed-patch outputs were discarded.

| Check | Evidence |
| :--- | :--- |
| Fresh workers | Sixteen distinct Codex CLI sessions; no worker was asked to role-play the other condition. |
| Actual workspace | Each session started in its own neutral root; the parent verified `pwd` and the visible manifest. |
| Guidance boundary | Guided roots contained the relevant skill only at `.agents/skills/task-quality/SKILL.md`; baseline roots had no `.agents` tree. |
| `AGENTS.md` boundary | Guided and baseline variants were separate; the baseline did not mention guidance, missing guidance, conditions, or `if-exists`. |
| Fixture parity | Each condition received the same fixture snapshot; code-review and security-review manifest hashes are in the machine record. |
| Trace boundary | Raw stdout, stderr, and JSONL were stored outside worker roots. |
| Worker blindness | Workers received natural prompts and files only—not assertions, expected behavior, labels, or grading instructions. |
| Parent grading | The parent inspected traces for leakage and graded the frozen assertions. |

No baseline trace contained the target skill identity, evaluation metadata, or
catalog paths. The corrected code-review rerun was fresh and used the same
protocol.

## Results

| Skill | Cases | Skill pass | Baseline pass | Better | Diagnostic decision |
| :--- | ---: | ---: | ---: | :---: | :--- |
| `code-review` | 4 | 11/13 | 11/13 | No | `INCONCLUSIVE` |
| `security-review` | 4 | 9/11 | 9/11 | No | `INCONCLUSIVE` |

The decisions mean “this run did not discriminate incremental skill value”; they
are not a recommendation to delete or rewrite these established skills, which
already have prior evidence under other harnesses. The cases and assertions
need a stronger follow-up before an efficacy decision is possible.

## Parent grading notes

### `code-review`

| Case | Skill | Baseline | Evidence |
| ---: | ---: | ---: | :--- |
| 1 matching | 4/4 | 4/4 | Both read the authentication contract and identified caller-controlled headers, the `401`/`403` error distinction, the admin-only routing defect, and the weak test with precise anchors. |
| 2 neighboring | 1/2 | 1/2 | Both avoided a diff review with no source; neither explicitly named `architecture-review`, so the routing assertion failed for both. |
| 3 ambiguous | 2/3 | 2/3 | Both requested code/scope and refused to invent findings; neither explicitly asked for the review question and contracts. |
| 4 edge | 4/4 | 4/4 | Both froze a semantic review point, traced the caller, removed legacy behavior, and public contract, separated contract/standards/test review, recorded dispositions, and made no edits. |

Both conditions found the real fixture defects. The skill produced a more
structured report, but the frozen assertions measured substantive coverage
that the baseline also achieved.

### `security-review`

| Case | Skill | Baseline | Evidence |
| ---: | ---: | ---: | :--- |
| 1 matching | 3/3 | 3/3 | Both identified spoofable identity, path traversal/absolute-path escape, missing per-user authorization, malformed input, and the vacuous test, with local verification guidance. |
| 2 neighboring | 1/2 | 1/2 | Both avoided inventing security findings from an absent project; neither explicitly named `systematic-debugging`. |
| 3 ambiguous | 1/2 | 1/2 | Both refused to claim an assessment without a project; neither explicitly established scope and authority. |
| 4 edge | 4/4 | 4/4 | Both detected guest fail-open behavior, fallback credentials, masked upstream failures, classified the dependency advisory as unconfirmed, and separated threat-model work. |

The guided output was especially explicit about evidence gaps and safe local
probes, but the baseline still satisfied the frozen assertions and reached the
same substantive findings.

## Interpretation

This is evidence that the current smoke assertions are too easy to
discriminate strong workers at this model/effort. They verify desirable review
content, but a capable baseline can infer much of that content directly from a
small, well-labeled fixture and a concrete prompt. The result weakens the
claim that the frontend skill is uniquely ineffective; it more strongly shows
that a tied result is not enough to judge incremental skill value.

It does not prove that the skills add no production value. A stronger follow-up
would use less self-describing fixtures, behavior-specific traps, harder
neighboring/ambiguous routing cases, and repeated fresh runs, while preserving
the parent-only grading and isolation protocol.

## Files

* Machine-readable result: [`2026-08-13-controls-gpt-5.6-luna-codex-max.json`](2026-08-13-controls-gpt-5.6-luna-codex-max.json)
* Matrix: [`validation-matrix.md`](../validation-matrix.md)
