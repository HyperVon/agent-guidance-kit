# Skill evaluation runbook

Operational method for evaluating the repository's skills. This runbook is the
practical, consistent companion to `skills/skill-evaluation/SKILL.md` and its
`references/isolation-protocol.md` and `references/evaluation-artifacts.md`.

The authoritative *rules* (what makes a run valid, how grading must be
evidence-backed, what counts as contamination) live in `SKILL.md`. This file
operationalizes them. Where this file and `SKILL.md` disagree, `SKILL.md` wins;
fix this file, do not weaken `SKILL.md`.

> **Why this document exists in its current form.** An earlier version of this
> methodology force-injected the target `SKILL.md` into the WITH-SKILL worker for
> *every* case — including routing/neighboring cases. That can measure
> post-activation behavior, but it **cannot establish routing quality**, because
> the router was never given a chance to decide. This runbook separates the two
> questions and removes the contradictions (condition labels in prompts, a
> baseline that was told its guidance was absent, OS isolation described as
> optional). Earlier pilot runs produced under this mixed method are preserved
> only as `protocol_status: exploratory` / `invalid` historical evidence and must
> not be read as protocol-valid proof.

## 1. Evaluation goals (three distinct concerns)

Keep these separate at all times:

1. **Routing quality** — when a natural user request arrives, does the harness
   select/load the correct skill? Does it avoid loading the target skill for a
   neighboring request? Does it resolve ambiguity per the documented routing
   contract?
2. **Post-activation / execution efficacy** — once a skill has *legitimately*
   been selected, does its guidance improve behavior relative to the harness
   default? (correctness, verification discipline, scope control, authority
   boundaries, etc.)
3. **Protocol validity** — were the two conditions actually independent and
   leak-free? Without this, any comparison is uninterpretable.

A conclusion about one of these must never be inferred from a run that only
measured another. In particular: **a forced post-activation handoff failure is
NOT evidence about routing.**

## 2. Case design

Each case set (`skills/<skill>/evals/evals.json`) contains five cases:

- 2 **matching** — clearly belong to the skill.
- 1 **neighboring** — belongs to a nearby skill or ordinary workflow.
- 1 **ambiguous** — requires clarification or a stated routing tie-breaker.
- 1 **edge / behavior** — a difficult boundary case.

Each case declares `evaluation_modes`: a subset of `["routing", "execution"]`.

- A **routing** case asks whether the *harness* selects this skill. It uses the
  natural user request verbatim and is **never** force-injected with the target
  skill.
- An **execution** case asks whether *this skill's guidance* beats the default
  once loaded. It deliberately provides the target guidance to the guided worker.
- A case may carry both modes (e.g. a matching case can test both "is it
  selected?" and "once selected, does it help?").

Do not assume every case is used for both modes. Keep oracles faithful to the
current `SKILL.md`; re-read the skill before scoring. Skill-design fixes that
the audit surfaces are a *separate* backlog item — do not edit a skill merely to
make its eval pass.

## 3. Routing evaluation protocol

Goal: measure the actual router.

1. Give the worker the **natural user request** from the case `prompt`.
2. **Do not** manually inject the target skill body, name, or path.
3. Let the real harness routing/discovery mechanism decide what is loaded.
4. **Capture which skill/guidance was selected or loaded** using harness
   evidence (loaded-skill manifest, startup log, tool-call that names a skill
   file, `AGENTS.md` projection, etc.). Prose self-report is not sufficient.
5. Evaluate:
   - **matching** → target skill should be selected/loaded;
   - **neighboring** → target skill should *not* be selected; the correct owner
     should be;
   - **ambiguous** → documented clarification or tie-breaker behavior should
     occur.
6. The routing test exercises the skill's **frontmatter `name` +
   `description`** (its discoverability surface), because that is what routing
   depends on. Keep that description accurate and distinct.

**If the harness cannot expose or verify the selected/loaded skill identity**,
mark the routing comparison **`protocol_status: limited`** (or `not_run`) and do
**not** infer routing quality from output prose. A forced-injection run must
never be recorded as a routing result.

## 4. Execution-efficacy protocol

Goal: measure the skill's marginal value once it is legitimately active.

1. Intentionally provide the target guidance to the guided worker (prefer the
   actual production skill-loading mechanism; if direct injection of `SKILL.md`
   is the only available approximation, record that as `protocol_status: limited`
   and label the run an approximation — never claim it "definitively matches the
   real harness" unless verified).
2. The other worker is the **harness default without the target guidance**
   (baseline). It does not receive the skill, its references, or any instruction
   to simulate absence.
3. Keep model, harness, reasoning effort, tools, network, and output location
   equivalent between conditions.
4. Clearly label this suite **execution / post-activation**. Its results are
   not evidence about routing.

**Optional placebo control.** Run a third condition with **irrelevant but
similarly sized guidance** (a different skill that does not apply to the task).
A benchmark that makes *any* long procedural prompt "win" is not trustworthy.
Use the placebo where the validity of the discriminator is in doubt; document
when it is required.

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
  `with-skill`, `baseline`, the case ID, or the experimental condition in any
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

- **Preferred:** committed deterministic fixtures under
  `skills/<skill>/evals/files/<case-id>/`. Each case's `fixture` block records
  `status: "ready"`, `type: "committed"`, `path`, and a `content_hash` (e.g.
  `sha256:…`). The validator checks the path exists and the hash matches.
- **Alternative:** a deterministic generator (`type: "generator"`) with
  versioned source, documented invocation, and a recorded output hash.
- Until a case has a reproducible fixture, mark it
  `fixture: { "status": "designed_only" }`. Do **not** claim an executable
  benchmark exists for it.
- Fixtures must be realistic (multi-file, with distractors/non-defects), must
  not reveal intentional defects in filenames/comments/task text, and must not
  contain personal paths, credentials, or private data.
- For Git-related fixtures, use a sanitized deterministic environment: isolated
  `HOME`, controlled `.gitconfig`, and fixture-specific identity. **Never** let a
  worker see the evaluator's real global Git identity, shell history, npm/pip
  config, GitHub CLI auth, SSH config, cloud credentials, or editor/harness
  config.

## 7. Running comparisons

- One WITH-SKILL (or routing) worker and one BASELINE worker per case on the
  same fixtures.
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
- Record per assertion: `guided` pass/evidence and `baseline` pass/evidence.
- Classify the outcome (see §9) and the measurement quality.

## 9. Status taxonomy

Do not reduce everything to `discriminating` / `non_discriminating`. Record three
independent dimensions:

- **Outcome category** (per case):
  - `skill_only_pass`
  - `baseline_only_pass`
  - `both_pass`
  - `both_fail`
  - `invalid`
  - `not_run`
- **Measurement status**:
  - `discriminating` — conditions differ on a meaningful case
  - `non_discriminating` — both pass or both fail (fixture too easy/ambiguous)
  - `inconclusive`
- **Protocol status**:
  - `valid`
  - `limited` (weaker fallback; e.g. instruction-only containment or injection
    approximation)
  - `contaminated` (environment or condition leak detected)
  - `invalid` (cannot be scored)
  - `not_run`

A `both_pass` case means something very different from `both_fail`; preserve the
distinction.

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
  isolation/boundary verification, loaded-guidance evidence (guided) and
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

For a protocol-valid run today in this CLI environment (OS containment
unavailable here), label runs `protocol_status: limited` and:

1. Build **frozen committed fixtures** per case (`fixture.status: "ready"` +
   `content_hash`); otherwise mark `designed_only`.
2. **Routing cases:** natural request, no injection, capture selected skill via
   harness evidence; if unavailable, mark `limited`/`not_run`.
3. **Execution cases:** provide target guidance to guided worker; harness-default
   baseline; optional irrelevant-guidance placebo.
4. Neutral names; no condition labels; boundary probe before scoring.
5. Fresh workers; equivalent settings; at least 3 repetitions for any confirmed
   efficacy claim.
6. Grade with quoted evidence; record full result schema; retain raw evidence in
   the ignored dir.
7. Resolve all contradictions with `SKILL.md` and `isolation-protocol.md`.
