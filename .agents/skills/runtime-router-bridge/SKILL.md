---
name: runtime-router-bridge
description: >-
  Coordinate optional Agent Runtime Router adoption with an existing Agent
  Guidance Kit project without copying router code, provider policy, or
  harness-specific guidance. Use when a target already adopts this kit and the
  user asks to add, audit, or adapt harness-aware subagent routing.
---

# Agent Runtime Router bridge

Use this skill only when the target already uses Agent Guidance Kit and the
user explicitly wants the separate Agent Runtime Router capability. This is a
thin coordination workflow: Agent Guidance Kit remains the owner of project
guidance, while Agent Runtime Router remains the owner of routing contracts,
target-local routing integration, discovery evidence, and supervised launch
boundaries.

## Contract

- **Inputs:** target repository, current Agent Guidance Kit adoption and
  guidance, an explicit Agent Runtime Router checkout or existing target-local
  installation, active-harness evidence, and the user's routing objective.
- **Output:** two linked but separately reviewable plans: the Guidance Kit
  guidance plan and the ARR mechanical/harness integration plan, with owners,
  conflicts, unknowns, approvals, and verification commands.
- **Default side effects:** none. Inventory, profile, discovery planning, and
  conflict checks are read-only. An explicit `--cache-output` discovery write
  is a separate approval.
- **Apply side effects:** only the unchanged approved Guidance Kit plan, the
  unchanged approved ARR installation plan, and separately approved
  target-local adapter/policy edits. Native worker execution requires its own
  approval.
- **Stop conditions:** stop on a missing or ambiguous ARR source, an existing
  routing owner, local divergence, a symlink or path conflict, unknown harness
  behavior, provider/credential access, or a plan that would create a second
  router.

## Ownership boundary

| Concern | Canonical owner | Bridge behavior |
| :--- | :--- | :--- |
| Project rules, skills, receipts, and harness projections | Agent Guidance Kit | Inventory and preserve; never copy ARR policy into them |
| Candidate eligibility, ranking, evidence, target blacklist, and cache | Agent Runtime Router plus the target project | Point to ARR contracts and target-owned files; never choose providers here |
| Harness-native discovery and launch syntax | Target-local ARR adapter | Require an explicit adapter contract; never infer commands or credentials |
| User approval and conflict handling | Both projects' existing plan/receipt workflows | Keep mechanical and semantic approvals separate |

Do not add provider catalogs, model lists, quota rules, credentials, worker
supervision, or ARR source code to Agent Guidance Kit. Do not use this bridge to
rewrite an existing model router; classify it as `KEEP_LOCAL`, `ADAPT`, or
`DEFER` and stop for the owning project's plan.

## Workflow

### Bound the planning phase

Keep the initial read-only inventory, harness profile, and two plan generation
steps to at most 30 minutes and 40 tool calls. Inspect target guidance and
explicitly named router/configuration files only. Exclude `.git`,
`.agents/.agent-runtime-router`, `.agents/runtime-router`, `.kilo/node_modules`,
`node_modules`, `.venv`, `venv`, `build`, `dist`, `target`, `.gradle`, `.local`,
`coverage`, `.idea`, `.cursor`, and `.vscode`; prefer `git ls-files` and bounded
`rg --glob` queries over recursive listings.

Do not run provider/model discovery, quota plugins, credential inspection, or
workers during planning without separate approval. If the budget expires or
evidence is incomplete, stop with `INCONCLUSIVE`/`BLOCKED` and list the missing
facts; never keep exploring, invent policy, or edit the target to make the plan
complete.

### 1. Establish the two sources

Read the target's applicable `AGENTS.md`, `.agents/AGENTS.md`, and
`.agents/OPERATING.md`, then read these canonical skills:

```text
<kit-root>/.agents/skills/bootstrap-project/SKILL.md
<kit-root>/.agents/skills/harness-adaptation/SKILL.md
<kit-root>/.agents/skills/agent-guidance-maintenance/SKILL.md
<arr-root>/.agents/skills/bootstrap-runtime-router/SKILL.md
<arr-root>/.agents/skills/agent-runtime-router-maintenance/SKILL.md
```

Resolve `<kit-root>` using the existing Guidance Kit maintenance rules. Resolve
`<arr-root>` only from, in order: an explicit path supplied for this
invocation, `AGENT_RUNTIME_ROUTER_ROOT`, the target's ignored ARR source
locator, or a validated adjacent `agent-runtime-router` sibling. Never search
unrelated personal directories, fetch a replacement, or embed an absolute
machine path in tracked files.

Validate that the ARR source is a real checkout containing `pyproject.toml`,
the bootstrap skill, and the maintenance skill. Record its revision and dirty
state in the plan; a dirty source is review evidence, not an invitation to
refresh or publish it.

### 2. Inventory before interpretation

Run the existing read-only Guidance Kit inventory:

```text
python3 <kit-root>/.agents/skills/bootstrap-project/scripts/inventory_project.py \
  --root <target-root> --format markdown
```

Then inspect, without executing target code or reading secrets:

- the Guidance Kit receipt and managed route block;
- all applicable instruction and harness entrypoints;
- `.agents/runtime-router/`, `.agents/.agent-runtime-router/`, and any ARR
  source locator;
- existing model/subagent routers, wrappers, route commands, provider/model
  catalogs, and project-specific blacklist/policy owners;
- target Git status, symlinks, and relevant build/test markers.

An existing router or stronger target owner is not an empty starting point.
Report it and stop the ARR portion until its owner and migration boundary are
explicit.

### 3. Build the active-harness profile

Use `harness-adaptation` to identify the active harness from session evidence,
documented behavior, and safe repository markers. Label unsupported or
unobserved capabilities `BEST_EFFORT` or `UNKNOWN`; do not infer a provider,
model, quota, authentication state, or launch command from a product name or
environment variable.

The profile must separate Guidance Kit projections from ARR adapter
capabilities. A harness that can read `AGENTS.md` is not thereby proven to
enumerate providers or launch a native subagent.

### 4. Generate two read-only plans

First create the normal Guidance Kit plan with `bootstrap-project`. Keep its
`ADD`/`ADAPT`/`KEEP_LOCAL`/`DEFER`/`SKIP` decisions and receipt boundaries.

Then create the mechanical ARR plan and the separate target integration
inventory:

```text
python3 <arr-root>/.agents/skills/bootstrap-runtime-router/scripts/install_runtime.py \
  plan --router-root <arr-root> --target <target-root> \
  --output <temporary-arr-plan.json>

python3 <arr-root>/.agents/skills/bootstrap-runtime-router/scripts/install_runtime.py \
  integration-plan --router-root <arr-root> --target <target-root> \
  --output <temporary-arr-integration-plan.json>
```

The integration plan may be `INCOMPLETE` for a fresh target. That is honest
missing adapter/profile evidence, not permission to invent a generic router.
If the target has an explicit adapter, run only its bounded discovery source
after the user approves that discovery step:

```text
python <target-root>/.agents/.agent-runtime-router/run.py harness discover \
  --target <target-root> \
  --config <target-root>/.agents/runtime-router/adapters/<id>/discovery.json \
  --pretty
```

Use `--cache-output` only for a separately approved refresh. A discovery
failure remains an ARR adapter error; never convert it to an empty catalog or
silently route through a second implementation.

### 5. Present the combined approval gate

Show a table with each file, owner, action, evidence, conflict, and approval:

| Scope | Owner | Action | Approval |
| :--- | :--- | :--- | :--- |
| Guidance Kit skills/route | Guidance Kit | `ADD`/`ADAPT`/`KEEP_LOCAL` | Guidance plan |
| ARR runtime/skills/route | ARR installer | mechanical plan/apply | ARR plan |
| `.agents/runtime-router/**` | Target + ARR contracts | adapter/profile/policy/cache | semantic integration plan |
| native worker launch | target harness + ARR supervisor | dry-run first, execute later | execution approval |

Do not combine these approvals into one “install router” action. Explicitly
list provider/model policy, blacklist, free/paid rules, unknown-evidence
switches, cache refresh, and launch behavior as target-owned decisions.

### 6. Apply only unchanged approved plans

After approval, apply the exact Guidance Kit plan and exact ARR mechanical plan
using their own `--approve` gates. Make semantic adapter edits only through the
target's approved integration plan. Use ARR's receipt-aware harness workflow
for a later switch:

```text
python <target-root>/.agents/.agent-runtime-router/run.py harness \
  plan-adaptation --target <target-root> --harness <new-id> \
  --output <temporary-adaptation-plan.json> --pretty
python <target-root>/.agents/.agent-runtime-router/run.py harness \
  apply-adaptation --target <target-root> \
  --plan <temporary-adaptation-plan.json> --approve --pretty
```

The switch must preserve the old adapter, target blacklist, and routing policy.
Any source, target, adapter, cache, or receipt drift requires a new plan.

### 7. Verify both boundaries

Run the Guidance Kit adoption validator and the ARR maintenance validator. Then
run ARR `harness profile`, `harness verify --dry-run`, `harness audit`, and a
harmless synthetic route using the target policy. Confirm:

- both managed route blocks coexist without overwriting each other;
- no Guidance Kit file contains ARR provider policy or copied runtime code;
- no ARR file contains Guidance Kit skill bodies or target-specific catalogs;
- the catalog cache is bounded, source-stamped, redacted, and ignored or
  tracked according to target policy;
- no credentials, prompts, raw provider errors, or personal paths entered
  tracked files;
- a second plan is a no-op or an explicit no-change result;
- a real provider/subagent call was not needed to prove installation safety.

Report each check as `PASS`, `FAIL`, `INCONCLUSIVE`, or `BLOCKED`, including
the exact source revision and target ref. Do not call a synthetic route proof a
real provider compatibility claim.

## Nearby requests that do not trigger this skill

- Adopting or refreshing Guidance Kit skills without runtime routing: use
  `bootstrap-project` or `agent-guidance-maintenance`.
- Reviewing ARR's router contracts or target adapter code: use ARR's own
  `agent-runtime-router`/maintenance skills or a code/security review.
- Choosing a provider/model for one task: use the installed ARR router; this
  bridge must not make that decision.
