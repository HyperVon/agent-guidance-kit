# Skill evaluation runbook

Operational method for evaluating the repository's skills. This runbook is the
practical, consistent companion to `skills/skill-evaluation/SKILL.md` and its
`references/isolation-protocol.md` and `references/evaluation-artifacts.md`.

The authoritative *rules* (what makes a run valid, how grading must be
evidence-backed, what counts as contamination) live in `SKILL.md`. This file
operationalizes them. Where this file and `SKILL.md` disagree, `SKILL.md` wins;
fix this file, do not weaken `SKILL.md`.

> **Why this document exists in its current form.** An earlier version of this
> methodology force-injected the target `SKILL.md` into the `target` worker for
> *every* case — including routing/neighboring cases. That can measure
> post-activation behavior, but it **cannot establish routing quality**, because
> the router was never given a chance to decide. This runbook separates the two
> questions and removes the contradictions (condition labels in prompts, a
> baseline that was told its guidance was absent, OS isolation described as
> optional). Earlier pilot runs produced under this mixed method are preserved
> only as `protocol_status: exploratory` / `invalid` historical evidence and must
> not be read as protocol-valid proof.

## 0. Development loop and harness boundary

The portable skills are the product. Use the cheapest experiment that answers
the current question:

1. static case/skill validation;
2. one-repetition `smoke` when runner mechanics need checking;
3. one-repetition `regression` for routine skill edits;
4. one-repetition `qualification` when the question is marginal value against
   a no-skill condition;
5. explicit `confirmation` only for important, high-risk, conflicting, or
   publication-bound claims.

The protocol is not tied to Kilo, Docker, a model provider, or any particular
agent CLI. New execution and regression runs use the JSON harness adapter
contract in [harness-adapter.md](harness-adapter.md). The adapter supplies the
worker/session boundary and proves guidance activation; the evaluator supplies
the task seed, hashes, condition comparison, and validation. Docker/Kilo is a
retained optional adapter for the strict historical confirmation path.

For a routine revision comparison, use:

```bash
python3 scripts/run_skill_regression_eval.py \
  --skill code-review --reference <previous-sha> --candidate HEAD \
  --case-id 5 --reps 1 \
  --harness-command 'python3 path/to/adapter.py'
```

For a fair target-vs-baseline qualification, use the same adapter boundary:

```bash
python3 scripts/run_harness_eval.py \
  --skill code-review --case-id 5 --protocol qualification --reps 1 \
  --harness-command 'python3 path/to/adapter.py'
```

The adapter command receives one JSON request on stdin and returns one JSON
response on stdout. It must use the same activation mechanism for candidate and
reference and must not rewrite guidance before context. The runner never
silently escalates to placebo or n=3.

When a result contains both `shared-outcome` and `skill-contract` assertions,
qualification verdicts are recomputed from shared-outcome and
universal-safety assertions only. A baseline cannot lose marginal-value credit
for target-only headings, terminology, workflow, or reporting rules.

## 1. Evaluation goals (three distinct concerns)

Keep these separate at all times:

1. **Catalog discriminability (Layer A)** — given a natural user request and a
   neutral skill catalog, can a model select the correct owner? This is a
   **portable model-as-classifier proxy**, not a harness-routing measurement. It
   cannot prove the real harness selects correctly — that requires Tier 3.
2. **Execution efficacy (Layer B, post-activation)** — once a skill has
   *legitimately* been selected, does its guidance improve behavior relative to
   the harness default? (correctness, verification discipline, scope control,
   authority boundaries, etc.)
3. **Protocol validity** — were the conditions actually independent and leak-free?
   Without this, any comparison is uninterpretable.

A conclusion about one of these must never be inferred from a run that only
measured another. In particular: **a forced post-activation handoff failure is
NOT evidence about routing.**

## 2. Case design

Three case tiers live in the repository:

- **`skills/<skill>/evals/evals.json`** (per-skill smoke + routing cases): five
  cases per skill by default — 2 **matching**, 1 **neighboring**, 1
  **ambiguous**, 1 **edge**. Each declares `evaluation_modes`: a subset of
  `["routing", "execution"]`.
- **`evaluations/confusion-sets/<name>.json`** — shared cross-skill discriminator
  cases grouped by cluster (the hardest cases). These host counterfactual pairs
  and workflow-transition turns. Every case prompt must avoid naming the expected
  skill.
- **`evaluations/holdout/<name>.json`** — holdout cases stored outside skill
  directories so ordinary edits do not consume them; used for generalization
  testing. Run them with the same runner as confusion sets:
  `python3 scripts/run_catalog_routing_eval.py --holdout
  evaluations/holdout/<name>.json --out .eval-evidence/holdout-<name>.json`.
  The runner records `evidence_type: "holdout"` (distinct from
  `"confusion-set"`), and holdout results are written only to `--out` — they
  never update development benchmark data.

Each per-skill case declares `evaluation_modes`: a subset of
`["routing", "execution"]`.

- A **routing** case asks whether the *harness* selects this skill (or, at
  Layer A, whether a catalog classifier selects it). It uses the natural user
  request verbatim and is **never** force-injected with the target skill. Its
  oracle lives in `routing` (expected selected skill for present/absent catalog
  conditions) and is graded from **harness-selection evidence**, not from whether
  the worker explains the choice.
- An **execution** case asks whether *this skill's guidance* beats the default
  once loaded. It provides the target guidance to the `target` condition only;
  the `baseline` gets no guidance and the `placebo` gets irrelevant guidance.
  Its oracle lives in `execution` (`expected_output` + `assertions`).
- A case may carry both modes (e.g. a matching case can test both "is it
  selected?" and "once selected, does it help?"). A routing-only case must not
  carry an `execution` block (no handoff-prose assertions), and an
  execution-only case must not carry a `routing`/`routing_context` block.

Routing and execution are **different oracles with different evidence**; a
post-activation handoff failure is NOT evidence about routing. See
[routing-experiments.md](routing-experiments.md) for the experiment types
(availability / description-regression / execution-efficacy).

Each case carries a `case_type` classifying its design intent (default `smoke`
for legacy per-skill packs; discriminator-family values live in confusion sets).
Do not assume every case is used for both modes. Keep oracles faithful to the
current `SKILL.md`; re-read the skill before scoring. Skill-design fixes that the
audit surfaces are a *separate* backlog item — do not edit a skill merely to
make its eval pass.

## 3. Routing evaluation protocols

Two routing protocols exist. They are **not interchangeable** and must not be
confused with execution conditions (target/baseline/placebo):

### 3a. Harness routing (Layer C — the real test)

Goal: measure the actual router. Only run this where the harness can capture
selection evidence.

1. Give the worker the **natural user request** from the case `prompt`.
2. **Do not** manually inject the target skill body, name, or path.
3. Let the real harness routing/discovery mechanism decide what is loaded.
4. **Capture which skill/guidance was selected or loaded** using harness
   evidence (loaded-skill manifest, startup log, tool-call that names a skill
   file, `AGENTS.md` projection, etc.). Prose self-report is not sufficient.
5. Evaluate:
   - **matching** → target skill should be selected/loaded;
   - **neighboring** → target skill should *not* be selected; the correct owner
     should be (in **both** the target-present and target-absent catalogs);
   - **ambiguous** → documented clarification or tie-breaker behavior should
     occur.
6. The routing test exercises the skill's **frontmatter `name` + `description`**
   (its discoverability surface), because that is what routing depends on. Keep
   that description accurate and distinct.

This is the **routing availability experiment** (catalog present vs target
removed). To measure a *description change* instead, run the **description
regression experiment** (candidate description vs prior description). See
[routing-experiments.md](routing-experiments.md).

**If the harness cannot expose or verify the selected/loaded skill identity**,
mark the routing comparison **`protocol_status: limited`** (or `not_run`) and do
**not** infer routing quality from output prose. A forced-injection run must
never be recorded as a routing result. Routing success is primarily the captured
selected skill, not a worker's self-report.

### 3b. Catalog discriminability (Layer A — portable proxy)

Goal: a portable, harness-independent check of whether skill descriptions are
distinct enough for a model to select the right owner. This is a **proxy**, not
a harness-routing measurement. `scripts/run_catalog_routing_eval.py`:

1. Build a neutral catalog from every skill's frontmatter (`name` + `description`).
2. For each case, construct a disambiguation prompt from the natural request +
   the candidate skill names from one confusion set (or the target skill + its
   neighbors). The candidate set is the **only** names the model may select.
3. Call the model once (no harness, no tools, no repo) and capture the
   structured `{"selected_skill": ...}` decision.
4. Compare against the expected skill, building a confusion matrix
   (intended-vs-selected) and a per-skill precision/recall table — recorded in
   the evidence's `aggregate` block. Counting rule: one observation per
   successful model decision; workflow-transition turns each contribute one
   observation; explicit null selections are the literal `"null"` class;
   precision/recall are `null` (not 0) when the denominator is zero.
5. Record the full matrix. A skill that routes correctly in isolation but is
   frequently confused with a neighbor by Layer A is a candidate for a
   description fix — but that fix is only validated by Layer C, not by Layer A
   alone.

### 3c. Confusion sets and discrimination

Confusion sets (in `evaluations/confusion-sets/`) are the discriminating cases for
Layer A. Each set groups a cluster of genuinely-confusable skills and contains:

- **hard-negative** cases — the expected skill is the closest plausible neighbor;
- **misleading-keyword** cases — security/review vocabulary that must NOT override intent;
- **counterfactual** pairs — same scenario, different deliverable (A: diagnose; B: act);
- **multi-intent** cases — two requested jobs, first priority must win;
- **ambiguous-natural** cases — genuine ambiguity where `expected_skill` is null
  (the router should clarify);
- **workflow-transition** cases — multi-turn, ownership must move between skills.

**Catalog-discriminability is a proxy.** Layer A accuracy never substitutes for a
captured harness-selection log at Layer C. Catalog routing results inform whether
descriptions are distinct enough to warrant a harness-routing experiment — they
do not themselves measure the harness router.

## 4. Execution-efficacy protocol (Layer B, harness-neutral)

Goal: measure the skill's marginal value once it is legitimately active.

The default implementation is the JSON harness adapter described in
`docs/evaluations/harness-adapter.md`. Use `scripts/run_harness_eval.py` for
smoke, qualification, or explicitly requested confirmation. The evaluator
creates independent condition workspaces and verifies task hashes; the adapter
starts the worker, activates guidance through the harness's normal mechanism,
and returns `worker_id`, `session_id`, `guidance_probe`,
`guidance_context_probe`, the workspace receipt read from the requested
workspace, and a worker-sourced execution attestation bound to the evaluator's
nonce, request, output, and return code. A local adapter without OS containment
or without an independently obtained worker attestation is
`protocol_status: limited`; only an adapter that proves an OS-level boundary
may claim `valid`.

The normal development workflow is a one-repetition regression comparison or
qualification. Do not add placebo or repetitions automatically. If a stronger
claim needs the retained Docker/Kilo procedure, run it explicitly as the
optional adapter below.

### 4a. Optional strict Docker/Kilo adapter

The following concrete procedure is retained for strict confirmation artifacts;
its Docker image, CLI, model gateway, and discovery path are not requirements
of the core protocol.

  1. Run **fresh, independent Docker containers** from a reusable image
    (`Dockerfile.eval`, built as `kilo-eval:local`) — one per condition:

    `target`, `baseline`, and optionally `placebo` (see
    `isolation-protocol.md` and `scripts/run_execution_eval.py`). For each
    repetition the runner derives **one pristine seed** from the fixture, then
    makes **one independent copy per condition** and verifies all copies
    hash-identically *before* the run — as TASK-state hashes that EXCLUDE the
    evaluator runtime treatment paths (`.kilo/skills`), so the target/placebo
    treatment trees cannot invalidate seed equality (full-filesystem hashes are
    recorded separately).
     The task workspace is mounted once, read-write, at `/work/task` (the
     worker's cwd); it is a *separate* copy per condition, so no worker can
     mutate another's state.
     - **Generator fixtures are evaluator-only.** The generator (`setup.sh`) is run
       under a sanitized environment (`eval_hashing.run_generator`) and its source is
       then **stripped** from the seed the worker sees. The worker must never read
       the generator source / answer key.
     - **Layer B is a POST-ACTIVATION experiment.** It answers "once guidance is
       active, does it improve task execution?" — it does NOT test whether Kilo's
       router chooses to activate the guidance (that is routing: Layer A/C).
       The evaluator therefore ACTIVATES the target and placebo guidance through
       the SAME deterministic mechanism: the runner places the skill's `SKILL.md`
       (+ `references/`) under `.kilo/skills/<name>/` inside the worker's
       workspace (the path Kilo scans at session start to discover project-level
       skills) and runs `kilo run --command "<skill>:skill"`, which resolves that
       command and injects the skill body into the worker context at session
       start. An unresolvable skill command makes `kilo run` exit non-zero
       ("Command not found"). The runner additionally exports the completed
       session inside the container and checks that the full body (after
       frontmatter) is present in the serialized user-context message. A
       successful command, hash-matched discovery probe, and
       `skill_context_probe: present` together prove that the intended guidance
       entered context.
       The placebo receives the same treatment with an irrelevant skill; the
       baseline receives no `.kilo/skills/` directory and no `--command`.
       Activation is proven per condition by: (1) the recorded resolved
       skill-command name, (2) an in-container boundary probe confirming the
       discovery path `SKILL.md` is present AND content-hash-matched
       (target/placebo) / the absence of any `.kilo/skills` tree (baseline),
       (3) the frozen `skill_content_hash` of the discovery tree, (4) the
       `skill_context_probe`, and (5) — when the model ALSO issues a native
       `skill` tool call — the parsed `activation_events` (real completed
       `tool_use` events with `part.tool == "skill"`, matching
       `state.input.name`, and a `<skill_content>` result; not arbitrary file
       reads). The validator rejects evidence where the target/placebo
       guidance was not activated through this mechanism.
       There is NO separate neutral guidance mount: an un-activated guidance
       copy on disk would conflate "guidance active" with "guidance present".
       The runner fails closed before Docker/Kilo worker launch when a target or
       placebo `SKILL.md` contains Kilo command-template placeholders such as
       `$ARGUMENTS` or positional `$0`, `$1`, and so on. These placeholders can
       substitute runtime arguments into the `:skill` command body, so the
       protocol cannot treat that source as unchanged guidance. The canonical
       skill files are read-only inputs; the runner never rewrites them.
  2. Use the free model through **anonymous Kilo Gateway access** (e.g.
    `kilo/tencent/hy3:free`); no API key or host auth is mounted into the
    container. `kilo run` inside the container needs `--auto` (permission
    auto-approval) to actually perform the task rather than auto-rejecting tools.
    - The model is **pinned**, not auto-routed: `--auto` is only permission
      auto-approval; model selection is fixed by `--model`. All conditions use
      the identical model so the comparison is fair.
    - **Free-model restriction is a cost-safety gate, not a scientific
      requirement.** The `require_free_model` guard refuses a non-`:free` model
      unless `--allow-paid-model` is passed. A paid model is methodologically valid
      as long as all conditions use the identical resolved model/runtime; the
      guard only prevents accidental spend. The free-model catalog changes over
      time — update `DEFAULT_MODEL` in `run_execution_eval.py` /
      `run_catalog_routing_eval.py` when the current free model is retired.
    - **The Kilo CLI version is pinned** in `Dockerfile.eval`
      (`ARG KILO_CLI_VERSION`); rebuilding the eval source never silently changes
      the worker runtime. The runner records `kilo --version`, the image id/digest,
      and node version in the evidence.
  3. Keep model, harness, reasoning effort, tools, network, and output location
    equivalent across all condition containers. Record all container IDs and
    session IDs; they MUST differ (a shared container means the conditions were not
    independent). The runner records, per repetition, the starting and ending
    fixture hashes and a filesystem snapshot (git diff / file listing) so the
    evidence proves all workers started from an identical seed and shows what each
    actually changed.
  4. **A failed run is not evidence.** If a Docker/Kilo invocation returns non-zero,
    the container never starts, the model output is unparseable/empty, or no session
    id is produced, the repetition is marked `run_status="failed"` and the validator
    **rejects** the whole evidence file. A broken, contaminated, or failed run can
    never masquerade as trustworthy evidence. A boundary probe inside the container
    confirms the activation discovery path `SKILL.md` is present and hash-matched
    (target/placebo) / that no `.kilo/skills` tree exists (baseline).
  5. **The natural task is byte-identical across all conditions.** The worker-visible
    prompt is the natural user request only — it must not name the skill, the
    condition, the case ID, or the evaluation. The runner records a
    `natural_task_hash` per repetition and the validator requires
    `natural_task_identical_across_conditions: true`.
  6. Clearly label this suite **execution / post-activation**. Its results are
    not evidence about routing.

**Placebo control is first-class.** For a strong efficacy claim, run three
conditions: `target` (real guidance), `baseline` (no guidance), and `placebo`
(irrelevant, similarly-sized guidance). The placebo is activated through the
EXACT SAME mechanism as the target (`--command <placebo>:skill` over its own
`.kilo/skills/<placebo>/` tree), so the comparison controls for "extra
procedural guidance" without depending on the router choosing to load
irrelevant guidance. If target beats baseline but placebo also beats baseline,
the benchmark may merely reward extra procedural prompting. Target guidance
should outperform placebo on skill-specific assertions. The placebo is required
for strong efficacy claims unless a documented reason makes it unnecessary.

## 5. Isolation

The baseline must not receive the target skill's name, path, description,
catalog entry, injection label, or skill-list metadata through any
system prompt, startup banner, tool manifest, or automatic projection. This is
non-negotiable and is verified, not assumed.

**Production-valid method (preferred):** each worker runs in its own
OS-contained root (container/sandbox/seatbelt profile) that denies traversal to
sibling roots, the catalog checkout, other worktrees, memory, and parent-only
logs. Only the worker root plus the runtime files required to start the harness
are visible. The worker's actual working directory is set by the harness, not
merely mentioned in a prompt. Capture stdout/stderr/session logs in a
parent-only directory the worker cannot inspect.

**Weaker fallback (must be labeled):** if OS containment is unavailable, an
instruction-only containment can be used **only** as `protocol_status: limited`,
never as valid. It must still:
  - use **neutral worker-visible names** — no `eval`, `evaluation`, the skill name,
    `target`, `baseline`, `placebo`, the case ID, or the experimental condition in any
    path, filename, or wrapper text;
- contain **no statements explaining that guidance is absent**, no expected
  outcomes, no assertions, no grader instructions, no disclosure that a
  comparison is happening;
- instruct the worker to operate only inside its directory and treat missing
  guidance as normal (never "check whether a guidance file exists");
- run a **boundary probe** (see `isolation-protocol.md`) before scoring; any
  successful unauthorized traversal contaminates the run.

If the harness cannot create and verify independent contexts — including absence
of target-skill identity in baseline-visible system metadata — record the
comparison as **invalid / not_run** and report the limitation. Do not score it.

## 6. Fixture policy

Fixtures must be **frozen and reproducible**, not silently reinvented per run.

### Task fixture vs routing projection

Keep two things separate:

1. **Task fixture** — source code, docs, test repo, PR text, and other
   user-visible task artifacts. It is identical across routing conditions.
2. **Routing projection (catalog)** — the harness's discoverable skill surface
   (name + description for every skill). It is generated per condition and may
   differ only in the dimension under test.

Generate the catalog with `scripts/build_routing_catalog.py` from each skill's
frontmatter. For the baseline, pass `--target-absent <skill>` so the target
entry is removed. **The catalog must never be committed inside a task fixture**:
doing so leaks the target's identity into the (shared) task fixture and makes the
target-absent baseline impossible to prove. A `catalog.md` found inside any
`evals/files/*` directory is a routing-surface leak and fails validation.

### Frozen fixtures

- **Preferred:** committed deterministic fixtures under
  `skills/<skill>/evals/files/<case-id>/`. Each case's `fixture` block records
  `status: "ready"`, `type: "committed"`, `path`, and a `content_hash` (e.g.
  `sha256:…`). The validator checks the path exists and the hash matches.
- **Alternative:** a deterministic generator (`type: "generator"`) with
  `source_hash` (the generator source) and `output_hash` (the generated output),
  plus `content_hash` mirroring `output_hash`. The validator **runs the generator
  in a sanitized temporary environment** and fails if the output hash is wrong or
  the generator is non-deterministic across two runs.
- Until a case has a reproducible fixture, mark it
  `fixture: { "status": "designed_only" }`. Do **not** claim an executable
  benchmark exists for it.
- Fixtures must be realistic (multi-file, with distractors/non-defects), must
  not reveal intentional defects in filenames/comments/task text, and must not
  name the intended skill or spell out the expected handoff unless the natural
  task itself contains that text. They must not contain personal paths,
  credentials, or private data.

### Generator determinism and Git environment

A generator fixture records both `source_hash` and `output_hash` (or equivalent).
The hashing tool:

1. creates a clean temporary directory;
2. sanitizes the environment (`HOME`, `XDG_CONFIG_HOME`, `GIT_CONFIG_GLOBAL`,
   `GIT_CONFIG_SYSTEM`, `GIT_CONFIG_NOSYSTEM`, author/committer identity,
   `EMAIL`, credential helpers, SSH/GitHub auth, shell history);
3. runs the generator exactly as documented;
4. canonical-hashes the generated output (for a git repo, the committed tree —
   content-addressed, so it is independent of author/date);
5. runs the generator again in another clean directory and asserts the two
   output hashes match;
6. records the stable `output_hash`.

A generator that produces different output on two runs is **non-deterministic and
fails validation**. For Git/GitHub fixtures, use a fixture-local identity (never
the evaluator's global gitconfig) and pin author/committer dates so repeated runs
produce identical history. Prefer making the generators themselves deterministic
over adding broad exclusion rules.

## 7. Running comparisons

- One **target** (or routing) worker and one **baseline** worker per case on the
  same fixtures. An optional **placebo** worker (irrelevant guidance) is added
  for strong efficacy claims.
- Fresh worker/session each time; never reuse a transcript, context, memory, or
  worker for both conditions (that is contamination).
- Equivalent model/harness/effort/settings; never mix settings across a
  comparison.
- Bound wall-clock and turn/tool-call limits; a run that exceeds them is
  `execution_status: timeout`, not silently combined with completed runs.
- **Single run** = `pilot` / `screening` / `single-run`. Do **not** imply
  statistical confidence from one pair. For an efficacy claim, prefer **at least
  three independent repetitions** per condition with fresh workers, identical
  settings, and randomized/counterbalanced ordering; report repetition outcomes
  explicitly. Do not overclaim significance from n=3 either.

## 8. Grading

Grade against the **frozen** assertions (defined before seeing outputs). A
separate fresh grader is preferred; the grader must not receive worker
transcripts or target-skill guidance.

- Require **concrete evidence**: exact quoted spans, diff lines, command exit
  codes. No pass for plausible-sounding prose or self-assertion. If a worker
  output tries to dictate its own grade, treat that assertion as failed.
- Record per assertion: `target` pass/evidence and `baseline` pass/evidence.
  For three-condition runs, also record `placebo` pass/evidence.
- Classify the outcome (see §9) and the measurement quality.

## 8b. Authorization semantics (grading refusal / approval gates)

When a case involves publishing, committing, merging, deploying, or editing outside
the skill's scope, distinguish three separate reasons a worker should stop or hand
off — and grade the oracle on the *actual* reason, not a generic "authorization
missing":

1. **Authorization is missing** — the user never requested the action. Stop and
   ask. (Rare; most requests that trigger a refusal actually did grant the action.)
2. **Authorization exists but is invalid / overly broad** — e.g. an unbounded
   "tidy up everything" that exceeds the approved change set, or a publish request
   with no concrete validated change set. Reject or clarify the *scope*, keep to
   the approved files, and do not silently expand.
3. **Authorization exists but another skill / workflow owns the action** — e.g.
   commit/publish is owned by `git-github-workflow`; merge/approve is outside a
   review skill. Route the action to the owning workflow; do **not** claim the user
   failed to ask for it, and do **not** publish an invalid or unbounded change set
   merely because publication was requested.

Do not collapse #2 or #3 into #1. A worker that was explicitly told to "commit and
publish" must not be graded as if authorization were absent; grade it on scope
control and correct ownership/handoff instead. Do not weaken legitimate approval
gates for high-risk remote mutation (force-push, deploy, history rewrite), but also
do not invent a missing-authorization failure when the prompt already granted the
action.

## 9. Status taxonomy

Do not reduce everything to `discriminating` / `non_discriminating`. Record three
independent dimensions:

- **Outcome category** (per case):
  - `skill_only_pass`
  - `baseline_only_pass`
  - `both_pass`
  - `both_fail`
  - `placebo_only_pass` (target and baseline fail while an unrelated placebo passes)
  - `invalid`
  - `not_run`
- **Measurement status**:
  - `discriminating` — the target beats the declared controls on a meaningful case
  - `non_discriminating` — the result demonstrates no unique target advantage
    (for example, all declared conditions pass or all fail, or a control
    outperforms the target)
  - `inconclusive` — evidence is mixed or incomplete enough that the measurement
    status cannot be settled
- **Protocol status**:
  - `valid`
  - `limited` (weaker fallback; e.g. instruction-only containment or injection
    approximation)
  - `contaminated` (environment or condition leak detected)
  - `invalid` (cannot be scored)
  - `not_run`

A `both_pass` case means something very different from `both_fail`; preserve the
distinction.

Protocol-valid execution result blocks additionally declare `protocol.conditions`
and `protocol.repeats`. Each case carries its own task and fixture hashes plus one
complete `repetitions[]` entry per declared repetition, with unique execution
identities. Limited or invalid historical records may retain the older compact
shape, but they must not be presented as valid evidence.

## 10. Evidence retention

Preserve auditable evidence; do **not** destroy the only copy immediately after
scoring.

- Store raw worker outputs, session logs, tool trajectories, and the boundary
  probe in an **ignored local run-evidence directory** (e.g.
  `.eval-evidence/`, see `.gitignore`). The committed result summary must remain
  sanitized.
- The committed result file still contains enough **quoted evidence** to justify
  each assertion decision, plus the required metadata (see `result-schema.md`):
  case/fixture/target-skill revisions, harness + version, model, reasoning
  effort, tool/network policy, worker/session IDs, actual working directory,
   isolation/boundary verification, loaded-guidance evidence (target) and
   explicit target-absence evidence (baseline), per-assertion grades with
  evidence, `skill_pass`/`baseline_pass`/`better`, protocol + measurement +
  outcome status, human-review notes, timing/token data, and contamination
  notes.
- **Cleanup (only after evidence is preserved):** delete disposable worker
  sandboxes once both outputs are graded and the raw copy is safely in the
  ignored evidence dir. Never delete the evidence dir.

## 11. Interpretation

- Do **not** compare raw "X/5" counts across unrelated skills as if they were a
  skill-quality score. Each five-case pack is a diagnostic suite testing
  different contracts and difficulties. You may report "3/5 cases showed a
  marginal difference in this suite," but not "this skill is stronger than
  another because 3 > 1."
- A single run is a pilot, not proof. Repeated confirmation is preferred for any
  efficacy claim.
- Preserve the useful qualitative lesson — strong base models may already perform
  obvious defect discovery well while specialized skills add marginal value in
  procedural discipline, routing boundaries, scope control, source-of-truth
  handling, verification, and authority constraints — as a **hypothesis /
  observed pattern**, not a proven law. Skills should still demonstrate positive
  task value, not merely more refusals.
- Avoid calling one model sample "authoritative." Prefer: *current recommended
  protocol*, *exploratory pilot*, *protocol-valid run*, *repeated confirmation
  run*.

## 12. Current recommended protocol (summary)

A **protocol-valid execution run is harness-neutral**. Use the following
development sequence:

- **Static checks first.** Validate the skill, frozen case, fixture, and
  assertion scopes without launching a model.
- **Regression for routine edits.** Compare candidate/reference revisions at
  n=1 with `scripts/run_skill_regression_eval.py` and the caller's harness
  adapter. Both sides contain the same skill; neither is a no-skill baseline.
- **Qualification for marginal value.** Use `scripts/run_harness_eval.py` with
  target/baseline at n=1 and a shared-outcome rubric. Record an honest early
  stop when the result is non-discriminating or the target clearly fails.
- **Confirmation only by explicit choice.** The retained Docker/Kilo path below
  is one optional strict adapter; another OS-contained adapter may support the
  same `valid` status if it proves the equivalent boundary and evidence.
- **Layer A (catalog-discriminability)** — the portable model-as-classifier proxy,
  not a harness-routing measurement: a fresh model call over a generated neutral
  catalog (no harness, no tools) that returns a structured `{"selected_skill": ...}`.
  See `scripts/run_catalog_routing_eval.py`. Confusion sets produce the confusion
  matrix.
- **Layer C (harness-routing)** — optional Tier 3; blocked where the harness cannot
  expose the selected skill as evidence; such cases fall back to Layer A or are
  marked `not_run`.

For any execution run:

1. Build **frozen committed fixtures** per case (`fixture.status: "ready"` +
   `content_hash`); otherwise mark `designed_only`.
2. **Routing cases:** prefer Layer A catalog-discriminability (portable,
   model-as-classifier) over a confusion set; use Layer C harness-routing when the
   harness exposes selection evidence. Catalog accuracy never substitutes for a
   captured harness-selection log.
3. Use one fresh worker/session per declared condition, identical natural task
   hashes, independent workspace IDs, and explicit guidance/context probes.
4. Keep `shared-outcome`/`universal-safety` assertions separate from
   `skill-contract` assertions. Never let target-only contract requirements
   lower a no-skill baseline's qualification score.
5. Treat failed/partial adapter responses as invalid evidence. Grade with
   quoted evidence; retain raw evidence in `.eval-evidence/`; validate with
   `python3 scripts/validate_evaluations.py --check-evidence`.
