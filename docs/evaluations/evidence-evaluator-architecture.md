# Promptfoo-backed evaluation architecture for Agent Guidance Kit

**Status:** Design-ready; M2 decision recorded (`GO WITH MATERIAL GAPS`); M3 authorized and pending implementation authorization

**Date:** 2026-08-23

**M2 decision:** `docs/adr/0001-promptfoo-backed-evaluator.md`

**Design input:** [shared conversation](https://chatgpt.com/share/6a8aafd3-322c-83ea-87c5-c49812cd88f4)

**Repository baseline:** `main` at `bfbd03d3f655c97a063dd945f2ee254f0b57e01d`

**Spike evidence commit:** `217d53f5db7ea01d4fd4fadbefdfe987f663cbb6`

**Validated Promptfoo version:** `0.122.0`

**Supersedes:** The first draft of this document, which captured the later
evidence-policy discussion but missed the earlier Promptfoo architecture and
repository-boundary decisions.

## 1. Executive decision

Do not continue evolving Agent Guidance Kit into a general evaluation engine,
and do not extract the current engine wholesale into a new general-purpose
`agent-skill-evaluator` framework.

The intended architecture is:

```text
                         reads/evaluates
agent-guidance-kit  <---------------------------+
  portable skills                               |
  adoption docs                                 |
  light static integrity                        |
                                                 |
                                   agent-guidance-kit-evals
                                     AGK corpus and suites
                                     AGK methodology/policy
                                     corpus generators
                                     routing metrics
                                     provenance validation
                                     Kilo integration
                                     historical AGK results
                                                 |
                                                 | configures/extends
                                                 v
                                            Promptfoo
                                      general evaluation engine
                                      providers and execution
                                      repeats/concurrency
                                      assertions and rubrics
                                      traces/telemetry/reports
```

The exact name `agent-guidance-kit-evals` remains provisional, but it describes
the product boundary better than `agent-skill-evaluator`: Promptfoo already
occupies the generic-engine role. The new project should contain AGK-specific
corpus, experimental semantics, integrations, and evidence—not another generic
provider/runner/assertion/reporting framework.

The migration is not approved merely because Promptfoo has relevant features.
The active compatibility spike must first demonstrate that Promptfoo can absorb
the clear majority of commodity mechanics such that the remaining custom
implementation is demonstrably limited to AGK-specific semantics, corpus
conversion, provenance, workspace controls, and genuine provider gaps. If the
migration requires a large parallel evaluator framework around Promptfoo, the
gate has not passed. Until it does, the current evaluator is the reference
implementation and must remain intact.

The later evidence-policy conclusions from the conversation remain governing
requirements:

- build an evidence system, not a certification system;
- maintain an intentionally sparse evidence database rather than an exhaustive
  Cartesian matrix;
- record exact harness, provider, model, reasoning, mode, and runtime identity
  where available, and explicitly preserve unknown/unreported values;
- separate observed facts from the documented confidence policy that interprets
  them;
- use adaptive scopes and repetitions proportional to the claim;
- state what is not tested;
- bound every claim to the evidence that actually exists;
- target “evidence suggests this skill does what it intends and is better than
  no skill,” not universal proof.

## 2. Decisions established by the conversation

The shared conversation evolved through three architectural positions. The
final design must preserve that chronology so an earlier recommendation is not
mistaken for the current decision.

### 2.1 First conclusion: AGK contains two products

The existing repository combines:

1. a portable copy/adapt skill library; and
2. a substantial evaluation framework with runners, schemas, validators,
   adapters, Docker isolation, case suites, holdouts, and historical results.

Those are coherent but separate products. AGK should return to its original
identity as a lightweight skill library. The evaluation corpus and methodology
remain valuable and should not be discarded.

### 2.2 Superseded conclusion: build a generic evaluator

The first split proposal was to create a general `agent-skill-evaluator` that
owned both the generic engine and AGK-specific suites. That proposal established
useful boundaries—external targets, external suites, separate target/evaluator
roots, preserved provenance—but it was superseded after reviewing existing
projects.

### 2.3 Current conclusion: Promptfoo owns the generic engine

The landscape/code-level comparison found substantial overlap between the
home-grown engine and Promptfoo's current Agent Skills support, including real
coding-agent providers, skill-use assertions, version comparisons, repetitions,
custom assertions, traces, telemetry, exports, and reports.

The revised recommendation is therefore:

> Extract AGK's evaluation corpus and methodology, not its generic evaluation
> engine. Use Promptfoo for execution mechanics and keep only the thin custom
> code required for AGK semantics, corpus conversion, provenance, workspace
> controls, and Kilo integration.

This decision is conditional on the compatibility spike. If preserving AGK's
semantics requires reconstructing a large evaluator around Promptfoo, the
standalone-engine option must be reconsidered rather than hidden behind wrapper
code.

## 3. Current state and migration gate

### 3.1 Evaluator v1

At the recorded baseline, the current repository owns:

- schema-v3 result records and protocol-v3 evidence;
- `smoke`, `qualification`, `regression`, and `confirmation` protocols;
- Layer A catalog discriminability;
- Layer B post-activation execution efficacy;
- Layer C harness-native routing semantics;
- target/baseline/placebo and candidate/reference runners;
- frozen fixtures, revision anchors, hashes, receipts, and attestations;
- per-skill eval packs, confusion sets, holdout, and historical results;
- Docker/Kilo strict-isolation infrastructure;
- a large custom validator and test suite.

This is the reference/control implementation for the spike. Its complexity is a
product-boundary problem, not evidence that its methodology should be weakened.

### 3.2 Promptfoo compatibility spike

An isolated Promptfoo compatibility spike is active. This architecture document
does not treat its in-progress implementation as validated evidence. The spike
report, actual runs, tests, v1/v2 comparison, and fresh-context review will
determine the migration decision. Live branch, version, and location details
belong in the companion milestone tracker and spike report.

**M2 decision outcome:** `GO WITH MATERIAL GAPS`. The spike demonstrated that
Promptfoo can replace commodity evaluation mechanics while AGK-specific code
retains corpus projection, experimental semantics, routing metrics, provenance,
workspace controls, Kilo integration, and strict-confirmation behavior. The
spike was not merged into `main`; historical evidence is preserved at
`docs/evaluations/promptfoo-spike/`. See
[ADR-0001](../adr/0001-promptfoo-backed-evaluator.md) for the full decision
record and the accepted gap batch. M3 is authorized.

### 3.3 Go/no-go gate

Proceed with the Promptfoo-backed split only if the spike demonstrates all of
the following:

- existing corpus JSON remains canonical and can generate Promptfoo tests;
- representative Layer A and Layer B experiments execute through Promptfoo;
- expected skill, actual skill, explicit null, and failed invocation remain
  distinct;
- baseline fairness is preserved;
- target and baseline use independent starting workspaces;
- at least one candidate/reference comparison preserves revision, actual
  starting target-content, and fixture identity;
- the frozen holdout is run only after implementation stabilization and is
  reported separately;
- v1/v2 differences are classified rather than hand-waved;
- Layer C is not claimed without appropriate provider evidence;
- Promptfoo absorbs the clear majority of commodity mechanics;
- remaining custom code is demonstrably limited to AGK-specific semantics,
  corpus conversion, provenance, workspace controls, and genuine provider gaps;
- the spike has not recreated a generic engine around Promptfoo.

The decision outcomes are:

| Outcome | Meaning | Next action |
| --- | --- | --- |
| `GO` | Promptfoo absorbs commodity mechanics and semantics remain intact. | Create `agent-guidance-kit-evals` and execute the staged split. |
| `GO WITH MATERIAL GAPS` | Core approach works, but bounded custom gaps remain. | Approve only explicitly costed gaps; rerun the gate after fixing them. |
| `NO` | Core semantics require a large parallel framework or results materially diverge. | Reconsider a standalone evaluator or a different engine. |
| `INCONCLUSIVE` | Spike lacks valid evidence. | Repair/extend the spike without changing AGK or consuming holdout as tuning data. |

## 4. Product boundaries

### 4.1 `agent-guidance-kit`

AGK's responsibility is to be a portable skill library:

- `SKILL.md` files and genuine skill-local references, templates, or scripts;
- README/catalog and adoption documentation;
- maintainer guidance for skill quality, portability, and boundaries;
- small deterministic repository-integrity checks;
- optional external link to the evaluation project.

AGK must not require Promptfoo or the eval repository to browse, copy, adapt, or
use a skill. It should not own model-backed evaluation CI, benchmark history,
holdouts, Docker workers, evaluator schemas, or per-skill eval fixtures after
the migration proves external evaluation works.

### 4.2 `agent-guidance-kit-evals`

The proposed eval repository owns:

- AGK-specific canonical case corpus;
- development confusion sets and protected holdouts;
- AGK experimental methodology and claim policy;
- projections/generators from canonical corpus to Promptfoo tests;
- AGK routing metrics and aggregation;
- baseline-fairness and protocol-claim validation;
- target/suite/fixture/revision provenance;
- independent workspace materialization where providers require it;
- Kilo-specific Promptfoo integration;
- optional strict Docker confirmation infrastructure;
- historical evaluator-v1 results and migration provenance;
- Promptfoo configuration and pinned integration tests;
- one reference target profile for external AGK checkouts.

It must not duplicate Promptfoo's generic CLI, provider framework, assertion
engine, concurrency system, report renderer, result UI, or built-in coding-agent
providers.

### 4.3 Promptfoo

Subject to spike verification, Promptfoo owns commodity mechanics:

- provider/model invocation;
- Codex, Claude, and OpenCode integration where supported;
- repeats, concurrency, retries, and caching controls;
- generic deterministic and model-graded assertions;
- skill-use and wrong-skill assertions;
- trace/trajectory collection;
- latency, token, and cost metadata;
- result export and human-facing reports/UI;
- generic provider extension interfaces;
- suite/test lifecycle hooks.

AGK policy may constrain how these features are used, but should not reimplement
them.

### 4.4 Target repositories

The evaluator must treat a target checkout as input. It must model these roots
separately:

- evaluator root;
- target root;
- suite/corpus root;
- output/result root;
- disposable workspace root.

Core integration must not assume the evaluator repository owns `./skills`, nor
may a target be required to contain `evals/`, confusion sets, or evaluator
scripts. A local path and a revision-addressable Git target should both be
supported.

## 5. Responsibility mapping

| Concern | Promptfoo | Thin AGK eval layer | Keep from evaluator v1? |
| --- | --- | --- | --- |
| Model/provider invocation | Own | Configure | No custom generic client |
| Codex/Claude/OpenCode providers | Own where supported | Validate evidence mapping | Do not recreate |
| Kilo provider | No native provider confirmed | Own or upstream | Reuse only bounded Kilo logic |
| Repeats/concurrency | Own | Declare policy | Retire generic orchestration |
| Generic assertions/rubrics | Own | Generate/configure | Retire duplicate engine |
| Skill-use assertions | Own normalized assertion | Interpret evidence source | Preserve Layer-C gate |
| Reports/UI/exports | Own | Add bounded AGK summary | Retire generic renderer |
| Layer A corpus/semantics | Execute calls | Own corpus, projection, metrics | Preserve and simplify |
| Layer B semantics | Execute conditions | Own fairness/claim policy | Preserve thinly |
| Layer C semantics | Expose provider metadata | Classify native/heuristic/forced/unknown | Preserve strictly |
| Placebo condition | Execute variant | Own protocol meaning | Preserve |
| Holdout discipline | Run explicit config | Own physical/policy separation | Preserve |
| Frozen assertions | Execute generated assertions | Own canonical declarations | Preserve |
| Provenance/version binding | Generic metadata | Own required envelope/validation | Preserve, simplify |
| Independent workspace | Provider-dependent | Own where required | Preserve invariants |
| Strict isolation | External/provider-specific | Optional Docker confirmation | Preserve as optional mode |
| Historical AGK results | No | Own migration/history | Preserve honestly |

## 6. Experimental semantics that must survive

### 6.1 Layer A — catalog discriminability

Layer A is an isolated classifier experiment:

```text
neutral catalog of skill names/descriptions + natural request
                            |
                            v
             selected skill, explicit null, or failure
```

It measures whether metadata is discriminable independently of a coding
harness. It includes matching, hard-negative, misleading-keyword,
counterfactual, ambiguous, multi-intent, workflow-transition, and bounded-review
cases. It does not prove a real harness activated a skill.

Promptfoo should execute the model/provider calls. A small AGK-specific module
should project canonical cases and calculate:

- attempted, successful, and failed decisions;
- correct and incorrect decisions;
- explicit null decisions;
- confusion matrix;
- expected vs actual per skill;
- precision/recall/F1 where denominators exist;
- workflow-transition correctness.

The decision-level invariant is:

```text
attempted_decisions = successful_decisions + failed_decisions
```

A successful explicit null is an observation. A provider failure is not null.
Decision accuracy uses successful decisions as its outcome denominator. The
attempted-decision denominator is retained for coverage and failure accounting;
failed or exhausted-retry samples are not recast as incorrect or null
decisions.

### 6.2 Layer B — post-activation efficacy

Layer B asks whether the intended guidance improves behavior after controlled
activation. Promptfoo executes target/baseline/placebo configurations and
assertions. The AGK layer owns the meaning and fairness of those conditions.

Conditions must start from independently materialized workspaces derived from
the same declared natural task/fixture and shared base target-content identity.
Condition-specific overlays—such as target skill installation, a clean
baseline, or placebo guidance—are applied after that shared base is established
and are recorded explicitly. Forced skill activation supports Layer B only; it
is not evidence of natural routing.

### 6.3 Layer C — harness-native activation

Layer C requires actual provider/harness evidence that the harness naturally
selected or loaded the skill. Evidence must retain its source classification:

| Classification | Example | Layer C claim |
| --- | --- | --- |
| `native` | First-class successful Skill/skill event naming the skill | Potentially supports Layer C after validation |
| `heuristic` | Successful read of a named `SKILL.md` | Limited; do not relabel as native |
| `forced` | Evaluator explicitly invokes/loads the skill | Layer B only |
| `behavioral` | Output looks skill-shaped | Does not prove activation |
| `unknown` / `none` | No reliable event | Layer C remains `not_run` or limited |

Promptfoo's normalized `metadata.skillCalls` is useful, but the AGK layer must
retain provider-specific source and success semantics rather than treating all
entries as equivalent proof.

### 6.4 Baseline fairness

Canonical assertions retain scopes:

- `skill-contract` — requirements only the target skill could know;
- `shared-outcome` — fair task-quality expectations across conditions;
- `universal-safety` — authority/safety constraints applicable to all.

Target may be graded on all three. Baseline and placebo are graded only on
shared outcome and universal safety. A no-skill baseline must not lose because
it did not reproduce a target-only taxonomy or report format.

### 6.5 Placebo

The optional irrelevant-guidance condition distinguishes specific skill value
from the generic effect of giving the model more structured instructions.
Promptfoo can execute the third configuration; AGK policy determines what claim
the three-way comparison supports.

### 6.6 Frozen assertions and holdout

Assertions and expected labels are defined before inspecting outputs. The
development corpus may be used to improve descriptions or integration. Pristine
holdout cases are physically and procedurally separate, are not used for tuning
while retaining holdout status, and are run only at an explicit generalization
checkpoint.

Infrastructure-invalid holdout runs may be replaced only when the invalidity is
recorded and model behavior from the invalid run is not used for tuning.

Once observed behavior from a valid holdout version is used to modify a skill,
routing rule, evaluator behavior, or expected outcome, that version has informed
development and is no longer pristine independent evidence for the next
generalization claim. It remains valuable as a regression suite, but should be
marked `consumed`, `retired_for_holdout`, or equivalent. When fresh independent
evidence is needed, supersede it with a new holdout version. This lifecycle rule
does not require secret-test infrastructure or elaborate holdout management.

### 6.7 Protocol validity versus task score

Promptfoo can report whether tests/assertions passed. The AGK policy layer must
still answer whether the comparison is controlled enough to support the stated
claim. A protocol-valid run can be non-discriminating. A high task score from a
limited or contaminated run cannot be upgraded to strong evidence by policy.

A comparison is not protocol-fair if an execution mode is structurally incapable
of performing the requested task and the result is interpreted as inferior
model or skill behavior. For example, a file-editing task run in a `plan` mode
that prohibits writes cannot be compared with `code: passed` as evidence that
the skill works worse in Plan mode. Target/baseline comparisons should normally
hold harness mode and permissions constant. Mode-sensitivity experiments may
vary them intentionally, but capability differences then form part of the
experiment and protocol validity must record whether each mode permitted the
intended operation.

## 7. Evidence and confidence model

### 7.1 Evidence interpretation principles

1. **Observed evidence is narrower than a general claim.**
2. **Missing evidence means unknown, not failure.**
3. **Cross-profile results support portability observations, not causal revision
   claims.**
4. **Controlled paired comparisons support improvement/regression claims.**
5. **Cached responses are not independent repetitions.**
6. **Retries are infrastructure events, not extra experimental samples.**
7. **Raw provider/harness configuration is preserved even when normalized.**
8. **Unknown semantics remain unknown.**
9. **Task capability must be compatible with harness mode for a fair
   comparison.**
10. **Confidence policy interprets evidence; it does not rewrite evidence.**

### 7.2 Intentionally sparse evidence

The long-term evidence store is not expected to fill every combination of:

```text
skill × case × harness × provider × model × reasoning profile
      × agent mode × protocol × repetition
```

Evidence accumulates through useful normal work. Each result retains its exact
scope and denominator so a three-case smoke result cannot be confused with a
51-decision qualification run.

Missing combinations are unknown/unobserved, not failures. No workflow should
require every skill × model × provider × harness × reasoning mode × agent mode
combination. Reporting should remain stratified by execution profile, for
example `Kilo + OpenRouter + Model A`, `OpenCode + Provider B + Model C`, or
`Codex + Model D + Max`. Do not compress materially different profiles into a
universal AGK score unless an aggregation is explicitly justified and the
underlying scopes, denominators, and per-profile breakdown remain visible.

### 7.3 Evaluation scope

Scope explains why a selection of cases was run; protocol explains the
conditions compared.

| Scope | Purpose |
| --- | --- |
| `smoke` | Small representative check that mechanics or basic behavior work. |
| `targeted` | Selected cases for a known weakness, model, or change. |
| `qualification` | Broader representative development/confusion evidence for an ordinary claim. |
| `holdout` | Untouched generalization check, reported separately. |
| `confirmation` | Repeated/broader/cross-environment evidence for an important claim. |

### 7.4 Claim levels

- **Observed:** this occurred in the named runs.
- **Supported:** multiple relevant observations point in the same direction.
- **Qualified:** representative evidence supports ordinary use in the tested
  environments.
- **Strongly supported:** repeated, broader, holdout, and/or cross-environment
  evidence agrees.

Never emit `proven`. Prefer “no regressions were detected in the tested cases”
over “there are no regressions.”

The vocabulary above is reporting language, not the basis for a generalized
claim-language generator. Cross-environment summaries should remain qualitative
and scoped, for example: “Strong across the tested higher-capability profiles;
some routing confusion observed in two lower-capability profiles.”

### 7.5 Evidence versus confidence policy

Durable raw observations are immutable records. Validation status, derived
analysis, and confidence interpretation are versioned and may be superseded
when new information or analyzer versions justify it. Original evidence is
never silently rewritten, and prior validation/analysis history is preserved
where practical. Start with one documented default AGK qualification policy,
factual evidence summaries, and explicit evidence gaps. Lightweight project/user
overrides are optional when a demonstrated need exists; a policy DSL,
generalized claim generator, or elaborate configuration taxonomy is not a v1
requirement. An unmet policy requirement produces a gap such as “no
cross-harness evidence available”; it does not erase evidence or label the skill
failed.

The default AGK qualification target is:

> The available evidence suggests this skill does what it is intended to do and
> provides benefit compared with no skill in the tested configuration.

That ordinarily requires representative positive and neighboring cases, a fair
no-skill comparison, no obvious tested material regression, and complete
provenance. It does not automatically require every model, harness, holdout, or
three repetitions.

### 7.6 Controlled comparisons and revision attribution

Cross-profile evidence is useful for portability, compatibility, coverage, and
generalization observations. Claims that a skill revision improved, regressed,
or preserved behavior should normally rely on controlled paired comparisons
that hold materially behavior-changing dimensions constant: harness and mode,
provider/gateway, model and reasoning profile, tools, permissions, task/fixture,
assertions, and system/agent mode where relevant. Candidate/reference runs use
the same or materially equivalent execution profiles unless the experiment is
intentionally studying their interaction.

When a gateway reports different resolved inference backends between
candidate/reference runs, treat that as a potential execution-profile confounder
unless evidence shows it is immaterial. Preserve and report known backend
identity without guessing or requiring pinning when the gateway does not expose
or control it; do not attribute unexplained differences solely to the skill
revision.

This is not valid revision attribution:

```text
revision A + Kilo + 0x Alpha = 88%
revision B + OpenCode + Laguna Thinking = 96%

therefore revision B improved the skill
```

The observations may reveal coverage or profile differences, but the skill
revision is confounded with the environment. **Cross-profile evidence describes
generalization. Controlled paired evidence supports revision attribution.**

### 7.7 Cache and retry semantics

Promptfoo owns caching and retry mechanics; AGK owns their evidence
interpretation.

An experimental repetition creates one experimental sample/decision. That
sample may contain one or more provider invocation attempts when Promptfoo or a
provider retries:

```text
experimental sample / decision
    └── one or more provider invocation attempts
```

- A cached provider/model response never counts as a new independent
  repetition. Cached artifacts may be reused for deterministic analysis and
  report generation, but must be identified as cached; model-behavior
  repetitions intended to measure stochastic behavior should normally disable
  response caching. Retain cache identity/version where material.
- A retry is a subordinate infrastructure event within the same experimental
  sample. It does not erase an earlier invocation failure and does not become an
  additional experimental observation.

Decision-level routing accounting still obeys:

```text
attempted_decisions = successful_decisions + failed_decisions
```

Invocation-level history separately retains, where applicable,
`provider_invocation_attempts`, `retry_count`, `retry_failures`, and
`retry_reasons`, or equivalent information. If an initial attempt fails and a
retry succeeds, the result is one successful decision with multiple invocation
attempts and the earlier infrastructure failure preserved. If retries are
exhausted, the result is one failed decision—not one decision per invocation.

```text
retry succeeds:   decisions attempted=1 successful=1 failed=0
                  invocations=2 retries=1 retry_failures=1
retries exhausted: decisions attempted=1 successful=0 failed=1
                   invocations=N retries=N-1
```

No custom caching or retry engine should be built around Promptfoo.

### 7.8 Adaptive testing

After migration, the normal workflow is:

```text
change skill
   -> smoke
   -> relevant targeted/confusion cases
   -> qualification if the change or claim warrants it
   -> holdout/cross-model/cross-harness confirmation only when justified
```

Repetition is also adaptive. A clear 1/6 failure may need no additional runs;
a 5/6 result with an interesting miss may warrant repetitions to distinguish a
systematic problem from stochastic variation. There is no universal repetition
count. Scope and repetitions should account for wall-clock/runtime, rate limits,
provider availability, free-tier availability, model availability, and cost;
long agent trajectories can make exhaustive repetition impractical even when
inference itself is free.

## 8. Execution-profile identity

The conversation explicitly treats runtime configuration as part of the
evidence, not incidental metadata. The exact raw setting supplied to the
harness/provider is authoritative. Derived normalized fields are secondary
interpretations and must never replace the raw value.

The behaviorally material `execution_profile` should record, where available:

- harness and harness version;
- provider/gateway and version where reported;
- requested and resolved inference provider/backend where a gateway reports
  them;
- requested model identifier;
- resolved/effective model identifier when knowable;
- model release/snapshot or alias resolution;
- model capability/tier label if known, without treating it as universal truth;
- reasoning mode: `reasoning`, `non_reasoning`, `hybrid`, or `unknown`;
- raw reasoning/preset configuration and any separately verified normalized
  interpretation;
- agent/harness mode such as `plan`, `code`, `ask`, `architect`, or custom;
- compound presets separately from model effort;
- system-prompt or mode-profile identity/hash where obtainable;
- tool and permission policy;
- network/sandbox/isolation policy;
- context/window or budget controls that materially affect behavior;
- context-management or compaction policy where configurable or observable and
  behaviorally material;
- relevant orchestration, including subagent behavior where material;
- environment characteristics such as OS, container, or runtime configuration
  when behaviorally material.

Sample/run metadata identifies the individual observation rather than the shared
behavioral configuration. It includes run ID, timestamp, repeat index,
seed/random controls, invocation/retry metadata, and cache metadata where
available. Different repetitions of the same behavioral configuration normally
remain one execution profile with multiple samples; repeat index or timestamp
alone does not create a new profile. Seeds are preserved faithfully as
sample-level experimental metadata unless an experiment explicitly declares
seed configuration to be a controlled profile dimension. This is a conceptual
distinction, not a requirement for a new schema.

Adjacent metadata should be retained without automatically changing behavioral
profile identity:

- `run_economics`: actual cost and cost class when available;
- `availability_metadata`: free-tier status at run time, rate-limit tier,
  availability status, and quota class when known.

These groupings are a conceptual distinction, not a requirement to over-design
a new schema.

Do not force all provider settings into a universal ordered enum. For example:

- non-reasoning is not merely `effort=low`;
- `instant` and `thinking` may be exposed execution profiles without proving
  anything about internal model architecture;
- a named preset may combine effort, orchestration, tools, subagents, or system
  behavior;
- labels such as `ultra` or `max` may have different semantics across
  harnesses/providers. Preserve the raw value and decompose it into reasoning
  effort, orchestration, or other effects only when those semantics are
  verified;
- `plan` versus `code` may change tools, permissions, and system instructions,
  not just a display label.

Unknown/null values are valid. Exact identifiers, versions, model snapshots,
resolved backends, and preset semantics should be recorded where available. If
a value is not knowable, retain `unknown`, `unreported`, an unresolved alias, or
equivalent rather than guessing. Missing version metadata is not itself a
protocol failure unless the applicable confidence policy requires it. Do not
infer `ultra > max`, `instant = non-reasoning`, `thinking = fixed reasoning`, or
a hidden backend without provider/harness documentation or runtime evidence.

Recommended shape:

```json
{
  "execution_profile": {
    "harness": {"name": "kilo", "version": "...", "agent_mode": "code"},
    "provider": {
      "gateway": "openrouter",
      "requested_backend": "auto",
      "resolved_backend": "unreported"
    },
    "model": {
      "requested": "provider/model-alias",
      "resolved": "provider/model-snapshot"
    },
    "reasoning": {"raw_setting": "ultra", "normalized": null},
    "tools": "...",
    "permissions": "..."
  },
  "run_economics": {"actual_cost": null, "cost_class": "unknown"},
  "availability_metadata": {"free_tier": true, "rate_limit_tier": null}
}
```

Layer A is harness-neutral and may validly record `harness: none` with an
`execution_context` such as `catalog_router`. Promptfoo is the evaluation engine
or orchestrator, not the coding-agent harness. For Layer A, meaningful identity
typically includes Promptfoo version, provider, model, raw reasoning/preset,
catalog projection, prompt, and corpus version. Layer B/C may additionally
include a coding-agent harness identity.

Model/provider freedom and support for inexpensive/free models are first-class
requirements. Claude-specific assumptions must not define the architecture.
Codex, Kilo, OpenCode, Command Code, non-reasoning models, reasoning models, and
future providers should all fit the same evidence model without claiming
identical behavior.

## 9. Canonical data and proposed repository structure

### 9.1 Canonical corpus

During the spike and initial migration, existing JSON remains canonical:

- `skills/*/evals/**` for per-skill cases and fixtures;
- `evaluations/confusion-sets/**` for development routing sets;
- `evaluations/holdout/**` for frozen holdout;
- committed schema-v3 results for evaluator-v1 history.

Promptfoo YAML/JSON is generated projection, not a second hand-maintained source
of truth. Do not combine engine migration with manual conversion of all suites.

After the split, canonical corpus moves to the eval repository, conceptually:

```text
agent-guidance-kit-evals/
  README.md
  AGENTS.md
  package.json
  pyproject.toml                    # only if thin Python extensions remain
  promptfooconfig.yaml

  profiles/
    agent-guidance-kit.yaml

  corpus/
    skills/<skill>/
      evals.json
      files/
    routing/
      development/
      holdout/

  generators/
    routing_cases.py
    skill_cases.py

  providers/
    kilo.py                         # if not upstreamed
    catalog_router.py

  assertions/
    protocol.py

  analysis/
    routing_metrics.py
    protocol_summary.py

  lib/
    hashing.py
    git_target.py
    workspace.py

  docker/
    Dockerfile.kilo
    preflight.py

  docs/
    methodology.md
    routing.md
    execution.md
    evidence.md
    profiles.md
    kilo.md
    migration-v1.md

  results/
    agent-guidance-kit/
      historical-v1/
      current/

  tests/
```

This is a responsibility map, not permission to create empty abstractions.
Directories should exist only when the spike or migration produces real code or
data for them.

### 9.2 Provenance envelope

Every durable result should bind:

- result/run ID and timestamp;
- Promptfoo version and config hash;
- eval-layer revision;
- target repository/path and target Git revision;
- actual starting target-content identity, including relevant local/uncommitted
  state;
- target skill identity and skill-tree hash;
- suite/corpus revision and suite hash;
- case IDs and expected-label/assertion hashes;
- fixture declaration and fixture hash;
- generated projection hash;
- execution profile, including provider/model and coding-agent harness where
  applicable;
- sample/run metadata, including repeat/seed and invocation/retry/cache identity
  where applicable;
- run economics and availability metadata where known;
- protocol, scope, conditions, and repetitions;
- workspace/isolation level;
- activation evidence source;
- raw Promptfoo artifact identity/hash;
- analyzer/policy version;
- validation status and known gaps.

Harness identity is not mandatory when no coding-agent harness exists. A Layer
A result may use `harness: none` and `execution_context: catalog_router`; it must
still bind Promptfoo, provider, model, raw reasoning/preset, projection, prompt,
and corpus identities. Cached status/cache identity and infrastructure retry
metadata are also retained where material so neither can be mistaken for an
independent observation.

The starting target content must be uniquely identifiable. A clean
revision-addressable Git checkout may be identified by its revision/tree. A
dirty Git target additionally requires the smallest robust identity for the
relevant uncommitted state, such as a dirty-state/snapshot hash or tracked-diff
and content-aware untracked-manifest hashes. A filename-only untracked manifest
is insufficient; it must represent file content, for example with path + content
hashes or an equivalent snapshot identity. A non-Git local target uses an
equivalent content snapshot/tree/manifest identity. Transient output outside the
evaluation's starting state is excluded. Candidate/reference comparisons must
not silently depend on unknown dirty state.

Historical v1 results retain their original schema and labels. Migration adds a
manifest/provenance note; it must not rewrite old limited or invalid evidence as
Promptfoo evidence.

### 9.3 Derived evidence index

Historical aggregation should be generated from durable raw result artifacts
using a selected/current analyzer and policy version. It must preserve
denominators and distinguish attempted, successful, failed, invalid, not-run,
and unavailable observations. The index is derived and rebuildable, not a
second independently editable source of truth. Explicit newer validation or
analysis may supersede an earlier interpretation—for example after discovering
workspace contamination—without mutating the raw artifact or silently erasing
the prior interpretation.

## 10. Kilo strategy

Model/provider freedom and practical access to inexpensive/free models are
project priorities. Kilo and similar provider-flexible harnesses are therefore
strategically important, but Kilo is not mandatory and must not distort the
harness-neutral methodology. OpenCode, Codex, and other environments remain
valid evaluation contexts.

If Promptfoo lacks a native Kilo provider, implement the smallest custom
provider that:

- receives Promptfoo prompt/config/context;
- materializes an independent workspace;
- installs the selected guidance or leaves baseline clean;
- invokes documented Kilo CLI behavior such as `kilo run --format json`;
- captures final output, return code, timeout/error, tokens, latency, model, and
  session identity;
- returns normalized Promptfoo provider metadata;
- maps reliable skill evidence into `metadata.skillCalls` while retaining
  `native`, `heuristic`, `forced`, or `unknown` source;
- refuses dirty-workspace retry or records mutation before retry;
- never claims native activation from output prose.

If Kilo emits a first-class successful skill event, it may support Layer C after
validation. A successful `SKILL.md` read is heuristic. Explicit command loading
is forced Layer B. No reliable event means Layer C stays `not_run`/limited.

The provider should be considered for upstream contribution. Long term, the
AGK eval repository should own Kilo only if Promptfoo cannot or will not.

## 11. Isolation and trust

Developer/qualification runs may use independent disposable host workspaces and
must report that isolation honestly. They do not inherit evaluator-v1's
strongest attestation merely because Promptfoo calls them “sandboxed.”

Strict confirmation may retain a smaller version of the Docker/Kilo worker and
preflight infrastructure, including the hardening already learned:

- private staging parent;
- correct `a+rwX` semantics;
- root-directory enumeration by non-owner workers;
- fail-closed permission normalization;
- cleanup after partial copy failure;
- deterministic non-owner probes;
- condition receipts/hashes where needed.

Trust layers remain conceptually separate:

1. provider/adapter claims;
2. evaluator-side consistency verification;
3. optional independent runtime/isolation attestation.

Promptfoo pass/fail does not automatically establish independent execution or
isolation proof.

## 12. File disposition after a successful spike

This is a planning classification, not authorization to delete files now.

| Current area | Expected disposition |
| --- | --- |
| `skills/*/evals/**` | Move to eval-repo canonical corpus. |
| `evaluations/confusion-sets/**` | Move to eval-repo development routing corpus. |
| `evaluations/holdout/**` | Move unchanged to protected eval-repo holdout. |
| `docs/evaluations/results/**` | Preserve under historical v1 results. |
| `SUMMARY.md`, validation matrix, routing/history reports | Move as historical/target-specific evidence. |
| `RUNBOOK.md`, protocol and evidence docs | Rewrite around Promptfoo mechanics while preserving AGK epistemic rules. |
| `harness-adapter.md` | Replace with provider evidence mapping and Kilo-specific integration docs. |
| `run_catalog_routing_eval.py` | Replace with Promptfoo config/provider plus thin routing metrics. |
| `run_execution_eval.py`, `run_harness_eval.py` | Replace generic mechanics with Promptfoo; retain only needed workspace/Kilo glue. |
| `run_skill_regression_eval.py` | Replace with Promptfoo comparisons plus thin Git revision materialization. |
| `compare_skill_evaluations.py` | Replace with focused evidence/history comparison if Promptfoo reports are insufficient. |
| `evaluation/**`, `evaluation_harness.py` | Retire commodity runner/adapter code; retain only demonstrated gaps. |
| `validators/**`, giant validator/test suite | Replace with narrow corpus and protocol/provenance validators. |
| `eval_hashing.py` | Reduce to skill, fixture, suite, projection, and revision hashing. |
| `Dockerfile.eval`, isolation preflight | Move/reframe as optional strict Kilo confirmation. |
| framework-bound `skill-evaluation` skill | Remove from AGK; optionally author a small framework-neutral skill later. |

No file is removed from AGK until the external eval repository can evaluate the
still-intact target and then the cleaned target.

## 13. Migration sequence

### Phase 0 — freeze evaluator v1

Record the AGK target SHA, current corpus/schema versions, deterministic gate,
historical result inventory, and optional tag/provenance marker.

### Phase 1 — complete the compatibility spike

Run representative Layer A, Layer B, baseline, revision, and holdout work from
canonical corpus. Produce `REPORT.md`, v1/v2 comparison, code-disposition
estimate, and fresh-context review. Do not split or delete.

### Phase 2 — make the go/no-go decision

Approve Promptfoo only from spike evidence. Explicitly cost material gaps and
reject unnecessary generic wrappers. Record the final engine decision in an
ADR.

### Phase 3 — create `agent-guidance-kit-evals`

Create the repository with Promptfoo pinned, a target profile, thin integration
code, tests, and provenance note. AGK remains unchanged and evaluator v1 remains
operational.

### Phase 4 — migrate canonical corpus and history

Copy/move per-skill suites, confusion sets, holdout, and historical results.
Prove the eval repository reads skill content from an external intact AGK
checkout and does not require target-local eval definitions.

### Phase 5 — migrate only necessary custom behavior

Port the demonstrated thin layer: corpus generators, routing metrics, policy/provenance
validation, Git target materialization, independent workspaces, and Kilo
provider. Use Promptfoo for commodity mechanics.

### Phase 6 — parity and non-regression

Compare v1 and Promptfoo-backed results on representative deterministic and
model-backed cases. Classify every material difference. Preserve historical
status and holdout discipline.

### Phase 7 — clean Agent Guidance Kit

Only after external evaluation works, remove evaluator-owned assets from AGK,
simplify README/AGENTS/CI, remove framework-bound `skill-evaluation`, and retain
only lightweight catalog/link/frontmatter integrity checks.

### Phase 8 — prove the cleaned target

Run the eval repository against cleaned AGK. Prove AGK works without the eval
checkout and eval-repo unit tests work without AGK using local fixtures/example
targets.

### Phase 9 — harden and upstream

Perform independent architecture/security review, fix trust/provenance gaps,
and propose generic improvements such as Kilo support or richer skill-call
evidence upstream to Promptfoo where appropriate.

## 14. CI and operational model

### AGK CI after split

Keep deterministic lightweight checks:

- each skill directory contains `SKILL.md`;
- frontmatter parses and names are unique;
- README catalog matches skills;
- relative links resolve;
- no dangling evaluator paths remain.

Do not make ordinary AGK PR health depend on external LLM availability,
Promptfoo installation, or model-backed evaluations.

### Eval-repository CI

Run deterministic checks on each PR:

- corpus/projection validation;
- thin integration unit tests;
- protocol/provenance rules;
- routing-metrics tests;
- hashing and fixture checks;
- Promptfoo config validation;
- lint/import/type checks as adopted;
- provider contract tests with local fakes.

Run model-backed evaluations manually, on schedule, or as explicitly approved
integration work. Record cost and provider/model identity. Free-model status is
not assumed to be stable.

## 15. Non-goals

- No repository split during the compatibility spike.
- No deletion of evaluator v1 before equivalence evidence.
- No new general provider, runner, assertion, report, or UI framework.
- No manual conversion of the entire corpus during engine migration.
- No skill/holdout tuning to improve migration results.
- No universal model/harness matrix requirement.
- No Kilo Layer C claim without reliable activation evidence.
- No database, service layer, web application, plugin marketplace, or remote
  orchestration platform for v1 of the eval repository.
- No requirement that skill consumers install Promptfoo.

## 16. Architecture acceptance criteria

The final architecture is successful only when:

1. Promptfoo has earned the engine role through the compatibility spike.
2. AGK is once again a coherent portable skill library.
3. The eval repository can evaluate an external cleaned AGK checkout.
4. AGK remains usable if the eval repository disappears.
5. The eval repository retains the canonical AGK corpus, holdout, methodology,
   provenance, and historical evidence.
6. Promptfoo owns generic mechanics and the custom layer remains demonstrably
   thin.
7. Layer A/B/C distinctions, failure accounting, baseline fairness, placebo,
   holdout, and protocol validity remain intact.
8. Execution profiles preserve raw provider/harness values and behaviorally
   material identity; Layer A may explicitly have no coding-agent harness.
9. Run economics and availability remain adjacent to, but distinct from,
   behavioral execution identity.
10. Evidence and confidence policy remain separate.
11. Revision claims rely on controlled comparisons; cross-profile evidence is
    reported as generalization or coverage.
12. Claims remain sparse, stratified, and bounded by actual scope, denominator,
    and tested configuration rather than a universal score.
13. Historical v1 evidence is preserved without relabeling.
14. Both repositories pass independent deterministic gates.
15. A fresh-context adversarial architecture review converges on no unresolved
    material findings before completion; repository push policy still applies.

## 17. Open decisions after the spike

**Resolved by M2 decision:**

- Does the evidence support `GO`, `GO WITH MATERIAL GAPS`, `NO`, or
  `INCONCLUSIVE`? → **`GO WITH MATERIAL GAPS`**. See
  [ADR-0001](../adr/0001-promptfoo-backed-evaluator.md).
- Is `agent-guidance-kit-evals` the final repository name? → **Selected as
  working name** pending M3 implementation. Recorded as the intended final name
  unless a concrete conflict is discovered.
- Which Promptfoo features are sufficiently stable to depend on directly? →
  **Pinned to `0.122.0`** for the initial migration; future upgrades verified by
  deterministic parity tests.
- Does Kilo expose native, heuristic, forced, or no usable activation evidence?
  → **Forced Layer B demonstrated; native Layer C not demonstrated.** Kilo
  exposes skill activation only through the CLI command surface, not a first-class
  native event.
- Which evaluator-v1 isolation guarantees remain mandatory for qualification,
  and which are reserved for strict confirmation? → **Independent disposable host
  workspaces for qualification; Docker attestation retained as strict
  confirmation** until M5/M6 determines the smallest necessary replacement.
- Which sanitized Promptfoo artifacts are committed versus retained as CI/release
  artifacts? → **Sanitized result representations committed** in
  `docs/evaluations/promptfoo-spike/`; full raw artifacts remain local-only
  under `experiments/promptfoo/.results/`.
- What exact default AGK qualification policy defines "evidence suggests
  benefit"? → Deferred to M3/M6.
- How are provider-native reasoning effort, reasoning mode, and compound
  harness presets normalized without losing original values? → Deferred to M3/M6.
- Is full Git history extraction worthwhile, or is a snapshot plus
  `MIGRATION.md` safer? → Deferred to M4.
- Which parts of the current framework-bound `skill-evaluation` skill should
  return later as a small portable methodology skill? → Deferred to M7.

The companion
[`evidence-evaluator-milestones.md`](evidence-evaluator-milestones.md) tracks
the spike gate and staged migration.
