---
source_commit: 217d53f5db7ea01d4fd4fadbefdfe987f663cbb6
status: historical M1 spike design note
supersession_policy: M2 corrections/interpretations do not silently rewrite this record
original_path: experiments/promptfoo/KILO-NEXT.md
date_copied: 2026-08-23
---

# KILO-NEXT: a Kilo provider for Promptfoo (design note)

Status: design only. This spike deliberately did NOT implement a Kilo
provider; the engine-compatibility question was answered with the same
`kilo` CLI the existing evaluator already uses (see `providers/`).

## 1. Proposed custom provider interface

A Kilo provider would be a small Python (or JS) Promptfoo custom provider:

```python
# providers/kilo_agent.py (future)
def call_api(prompt, options, context):
    cfg = options.get("config", {})
    # kilo run --format json [--command <skill>:skill] --auto --pure <task>
    # cwd = an independent workspace materialized per case x condition x rep
    return {
        "output": <collected text parts>,
        "error": <None or failure string>,
        "metadata": {
            "session_id": ..., "returncode": ...,
            "tokenUsage": {"input": ..., "output": ...},
            "latencyMs": ..., "cost": ...,
            "skillCalls": [...],   # see section 6
            "workspaceState": {...},
        },
    }
```

Promptfoo supplies orchestration, repetitions, assertions, caching control and
result export, exactly as in this spike. The provider owns only: workspace
materialization, `kilo run` invocation, JSON-stream parsing, and metadata
normalization.

## 2. Expected use of `kilo run --format json`

* `--pure "<natural task>"` — worker-visible prompt is the natural task,
  byte-identical across conditions (treatment boundary preserved).
* `--model kilo/<provider>/<model>` — model identity recorded in provenance;
  identical across conditions.
* `--command <skill>:skill` — deterministic post-activation for target /
  placebo conditions (Layer B). RC=0 proves discovery+activation of that
  SKILL.md.
* no `--command`, no `.kilo/skills` tree — baseline condition.
* `--auto` — required whenever the task may need tools (agentic execution
  cases); not needed for pure-text routing calls.
* `--session <id> --continue` — multi-turn workflow-transition chaining within
  one repetition.

One operational caveat discovered in this spike: `kilo run` resolves the
project (and therefore `.kilo/skills/`) from the `PWD` environment variable.
Programmatic callers must set both `cwd=` **and** `PWD` in the child
environment, otherwise skill-command discovery silently targets the wrong
project root.

## 3. Independent workspace handling

Same protocol as this spike (`lib/workspace.py`):

1. pristine seed from the frozen fixture (`eval_hashing.materialize_fixture_seed`,
   generator sources stripped);
2. one fresh host directory per `case x condition x repetition`
   (`/tmp/kilo/agk-pf-workspaces/<run>-case<id>-<condition>-r<rep>`);
3. runtime treatment installed at `.kilo/skills/<skill>/` (target/placebo)
   or absent (baseline);
4. starting/ending TASK-state hashes exclude `.kilo/skills`; full-filesystem
   hashes recorded separately when needed.

Isolation level remains "independent disposable host workspace". The Docker
attestation path stays the strict-confirmation reference.

## 4. Skill directory installation

Install the canonical repo skill into `<workspace>/.kilo/skills/<name>/`:
`SKILL.md` plus `references/`. For revision comparisons, project
`git show <sha>:skills/<name>/SKILL.md` (+ references via `git archive`) so
candidate/reference rows differ only in the skill revision.

## 5. Token / latency / error metadata

The `--format json` event stream carries per-step `tokens`, `cost`, and
timestamps. The provider would aggregate:

```json
{
  "tokenUsage": {"prompt": N, "completion": M, "total": T},
  "latencyMs": <wall clock of the invocation>,
  "cost": <summed step cost>,
  "error": null
}
```

Invocation failures must surface as ProviderResponse `error` — never as an
empty output or a fabricated decision (failure-accounting requirement).

## 6. Mapping activation evidence to `providerResponse.metadata.skillCalls`

Kilo currently exposes skill activation through its command surface
(`--command <name>:skill`) rather than through a first-class "Skill tool"
event in the public JSON stream. The mapping would be:

| Evidence source | Normalized form |
|---|---|
| `--command <name>:skill` accepted, RC=0 | `{"skill": name, "evidence": "forced"}` |
| successful file read of `.kilo/skills/<n>/SKILL.md` visible in tool events | `{"skill": n, "evidence": "heuristic-read"}` |
| explicit native Skill-tool event (if a future Kilo version emits one) | `{"skill": n, "evidence": "native"}` |

Only the third row may support a Layer C ("harness-native activation") claim.

## 7. What JSON event evidence would be needed before calling activation "native"

An event that names the skill as a first-class action taken by the model, e.g.:

```json
{"type":"tool_call","part":{"tool":{"name":"skill","input":{"skill":"code-review"}}}}
```

Requirements: tool name identifies the skill surface (not a generic read),
the input names the activated skill, and the event is emitted for the session
in which the task ran. Anything inferred from file reads is heuristic by
definition.

## 8. If Kilo exposes only successful file reads

Treat reads of `.kilo/skills/<n>/SKILL.md` as heuristic evidence:
`evidence="heuristic-read"`. Report Layer C status as `not_run` /
`not_demonstrated` unless the experiment design separately forces activation
(Layer B) or captures native events (section 7). Never upgrade a heuristic
signal to "native".

## 9. If Kilo exposes no reliable activation evidence

Record `activation_evidence: "none"` and keep Layer C claims disabled
(`layer_c_status: "not_run"`). Forced-activation experiments (Layer B) remain
fully valid because they do not depend on observing native activation — the
evaluator activates deterministically via `--command` and verifies RC=0 plus
the installed content hash.
