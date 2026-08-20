# Evaluation isolation protocol

Progressive-disclosure companion to `skill-evaluation`. Load this only when
setting up or troubleshooting worker isolation for a clean-context evaluation.
The safety invariants that decide whether a run is valid stay in `SKILL.md`;
this file holds the filesystem/sandbox procedure and troubleshooting.

## Filesystem and harness containment

- For Codex CLI, use a task-matched sandbox. Report-only tasks may use an
  isolated write-enabled root so the parent can verify that no edits occurred;
  implementation or test-hardening tasks require write access. Use read-only
  only when the task genuinely requires no writes, and record that limitation
  when it makes a no-edit assertion uninformative.
- Capture stdout, stderr, and session JSONL in a parent-only directory outside
  every worker root; never redirect them into a worker workspace, because the
  worker can inspect its own trace.
- A neutral name is not filesystem isolation: when the harness allows parent
  traversal, the worker must not be able to enumerate sibling roots, the
  catalog checkout, other worktrees, memory, or parent-only logs.
- Use an OS-level jail, container, or equivalent profile that denies those paths
  and allows only the worker root plus the runtime files genuinely required to
  start the harness.

## Worker environment separation

- Each worker runs in its own root containing only the declared fixtures; do not
  place workers in a shared temporary parent, repository collection, or workspace
  whose siblings the agent can inspect.
- Restrict file, tool, and network access to the case when the harness supports
  it; otherwise state the limitation and exclude any run contaminated by
  unrelated discovery.
- Set the worker's actual working directory, or have the runner verify `pwd` and
  an immediate file manifest before the task begins. A path mentioned in a prompt
  is not isolation.

## Execution isolation tiers

The execution efficacy layer (Layer B) runs each condition worker in a fresh
container. The isolation tier determines the protocol status that is achievable:

- **Tier 1 — fast developer mode** (sanitized environment, no OS sandbox): use
  only for prompt iteration and cheap discrimination checks; always mark
  `protocol_status: limited`.
- **Tier 2 — strict isolated** (Docker OS-level containment): the only tier that
  can reach `protocol_status: valid` for execution efficacy. Each condition runs
  in a **fresh Docker container** built from `Dockerfile.eval` (image
  `kilo-eval:local`), with a verified boundary probe.

  - **Fresh container per condition.** `target`, `baseline` (and optional
    `placebo`) are *separate* `docker run --rm` invocations; record all
    container IDs and session IDs — they must differ. A shared container means
    the conditions were not independent (contamination).
  - **Independent seed copies.** For each repetition the runner derives **one
    pristine seed** from the fixture, then makes **one independent copy per
    condition** and verifies all copies hash-identically *before* the run —
    as TASK-state hashes that EXCLUDE the evaluator runtime treatment paths
    (`.kilo/skills`). The condition workers never share a mutable fixture: each writes
    only to its own copy mounted at `/work/task`. Full-filesystem hashes
    (treatment included) are recorded separately.
  - **Controlled post-activation for the target condition.** Layer B is a
    POST-ACTIVATION experiment: it answers "once guidance is active, does it
    improve task execution?" and must NOT depend on whether Kilo's router
    chooses to activate the guidance (that is routing — Layer A/C). The runner
    therefore ACTIVATES the target guidance deterministically: it copies
    `SKILL.md` + `references/` into
    `.kilo/skills/<name>/` inside the worker's workspace (the path Kilo scans
    at session start for project-level skills) and runs
    `kilo run --command "<name>:skill"`, which resolves that skill command and
    injects the guidance body into context at session start. An unresolvable
    skill command makes `kilo run` exit non-zero, so a successful run (RC=0) is
    machine-verifiable proof that the discovery tree existed and the command
    resolved. The runner then exports the completed session and requires the
    full skill body (after frontmatter) to be present in the serialized
    user-context message. **Never copy the whole skill directory**: doing so would
    leak the `evals/` fixture snapshot (including the expected output) into the
    worker.
    The placebo condition activates a different (irrelevant) skill's guidance
    through the EXACT SAME mechanism.
  - **Generator fixtures are evaluator-only.** The generator (`setup.sh`) is run under a
    sanitized environment and its **source is stripped** from the seed the worker sees, so
    the worker never reads the answer key / construction logic.
  - **No guidance for the baseline.** The baseline container receives the same task
    fixture and the same natural task, but **no `.kilo/skills` discovery tree and no
    `--command`** — it must not see the target `SKILL.md` body, its `references/`, or the
    skill name in a guidance path.
  - **No host secrets.** The image contains no `~/.gitconfig`, no `~/.ssh`, no
    `GH_TOKEN`/`GITHUB_TOKEN`, and no mounted Kilo auth store. Models are reached through
    **anonymous Kilo Gateway access** (`kilo/tencent/hy3:free`) — absence of
    `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` does **not** mean there is no provider. `kilo
    run` inside the container needs `--auto` (permission auto-approval) to execute rather
    than auto-reject tools. The **Kilo CLI version is pinned** in `Dockerfile.eval`
    (`ARG KILO_CLI_VERSION`) so rebuilding never silently changes the worker runtime.
  - **Deterministic, non-attributable git identity.** `HOME=/home/eval` with
    `user.name "Eval Worker"` / `user.email "eval-worker@example.invalid"` baked into the
    image, so any git work the worker does cannot leak the host author.
  - **Activation boundary probe inside the container.** After the run, a probe checks
    `.kilo/skills/<name>/SKILL.md` **presence + content-hash match** (target/placebo) /
    **absence of any `.kilo/skills` tree** (baseline). The runner records
    `skill_probe` (`present`/`absent`/`hash_mismatch`) and
    `skill_context_probe` (`present`/`none`) from these probes; a bare text
    claim is not accepted. When the model ALSO issues a native `skill` tool call,
    the runner parses those real completed `tool_use` events as
    `activation_events` (supplementary evidence; a normal file `read` is NOT
    activation).
  - **Failure is not evidence.** A Docker/Kilo invocation that returns non-zero, never
    starts a container, produces empty/unparseable model output, or yields no session id is
    recorded `run_status="failed"`; the validator **rejects** the whole evidence file.
  - **Boundary probe before scoring.** Run `scripts/docker_isolation_preflight.py`
    (`--image kilo-eval:local`). All boundary checks must pass: isolated home, deterministic git
    identity, no ssh dir, no token env, no host `.gitconfig`/path leak, no mounted Kilo
    auth, **target skill discovery tree absent in the baseline workspace** AND **present,
    readable, hash-matched, and with references in the target/placebo workspace** at the
    real `.kilo/skills/<name>/SKILL.md` discovery path. Any failure invalidates the run.

## Boundary probe

Run a parent-side boundary probe before scoring:

```text
pwd               # worker's actual working directory
local manifest    # files the worker can see
parent traversal  # attempt to reach sibling roots / catalog checkout / parent-only logs
catalog-path access # attempt to reach the target skill or its references
```

Any unexpected success contaminates the condition and invalidates the run.

### Codex CLI sandbox note

For Codex CLI on macOS, the inner sandbox may block a nonstandard contained
root. After verifying an outer `sandbox-exec`/seatbelt profile, the runner may
use `--dangerously-bypass-approvals-and-sandbox` so that the outer profile remains
authoritative; never use that flag without verified outer containment, and record
the profile and denied-path probes.

## Isolation-failure troubleshooting

| Symptom | Meaning | Action |
| :--- | :--- | :--- |
| Worker starts in the catalog repository or can see sibling evaluation metadata | Condition is contaminated | Discard the run |
| Baseline worker receives the target skill's name, path, description, catalog entry, injection label, or skill-list metadata through system prompt, banner, tool manifest, or other automatic projection | Condition is contaminated even if skill text is not loaded | Mark contaminated, do not score |
| Discovered `AGENTS.md` guidance carries the injection | The baseline may leak the condition | Use separate neutral variants; the `target` variant may name a neutral guidance path, the baseline must not mention that path or use an `if-exists` check |
| Harness cannot create and verify independent contexts (including absence of target-skill identity in baseline-visible system metadata) | No valid comparison possible | Leave the matrix untested, report the limitation |
| An interrupted pair, partial case, or model-switch run | Mixed with completed result | Exclude rather than silently combine |
