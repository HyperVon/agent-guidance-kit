# Evaluation validation matrix

Status dimensions are kept separate (per the corrected methodology):

- **Fixtures** — `ready` (frozen committed fixture with `content_hash`) vs
  `designed_only` (case defined, not yet executable).
- **Routing** — does a *harness-selection* run exist? (real router, captured
  selected skill). `not_run` unless measured that way.
- **Execution** — does a *post-activation* run exist? `exploratory` (force-injected,
  instruction-only, historical) vs `pending` vs `valid`.
- **Protocol** — `valid` / `limited` / `invalid` / `not_run`.
- **Repeats** — number of independent repetitions per condition (pilot = 1).
- **Result** — link to the per-skill result file.

> **Important:** The four skills below with result links contain only
> `protocol_status: invalid` / `decision: exploratory` historical pilots. They do
> **not** constitute validated evidence. No routing result exists for any skill
> yet (all force-injected, so routing is unmeasured). No cross-skill "X/5"
> comparison is a skill-quality score.
>
> **Phase 1 reassessment (2026-08-16) + follow-up:** the corrected pipeline was
> exercised in this CLI environment. The fixture/hashing/catalog/validation half
> runs green (fixtures idempotent, catalogs generate for both conditions, validator
> + 29 tests pass). A protocol-valid run on the **macOS host** is still not possible
> (Kilo/CLI on a laptop is the harness itself: it cannot capture routing selection as
> harness evidence, and cannot create independent OS-contained worker contexts — host
> `gitconfig`/`gh` token present). **However, Layer B (execution) now runs inside
> Docker** (`Dockerfile.eval` → `kilo-eval:local`: fresh containers, deterministic
> git identity, no host secrets, no mounted auth, anonymous free model
> `kilo/tencent/hy3:free`), and **Layer A (catalog-routing) is fully portable** and
> runs on the host. Both were smoke-proven on the `code-review` pilot (distinct
> container IDs; guided applied the skill vs baseline refusal; catalog-routing
> selected the target when present and declined when absent). **Layer C
> (harness-routing) stays `not_run`** where the harness cannot expose the selected
> skill. Net: for the four pilot skills **execution infra = proven**,
> **catalog-routing = proven**, **harness-routing = `not_run` (blocked)**,
> protocol `not_run` (no graded n≥3 run published yet), repeats 0. The historical
> exploratory pilots remain `invalid` and were not reused.

**Target harness:** Kilo/CLI  |  **Model:** kilo/tencent/hy3:free (anonymous, free)  |  **Reasoning effort:** high
**Isolation available:** Layer B uses **Docker OS-containment** (`isolation_method: docker`,
production-valid); host-only runs are still instruction-only and must be labeled `limited`.

| Skill | Cases | Fixtures | Routing | Execution | Protocol | Repeats | Result |
| :--- | :---: | :--- | :--- | :--- | :--- | :---: | :--- |
| [adversarial-pr-review](../../skills/adversarial-pr-review/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [ai-slop-detector](../../skills/ai-slop-detector/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [architecture-review](../../skills/architecture-review/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [code-review](../../skills/code-review/evals/evals.json) | 5 | ready (5/5) | not_run | exploratory (force-injected) | invalid | 1 | [results](results/code-review.md) |
| [codebase-orientation](../../skills/codebase-orientation/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [dependency-upgrade](../../skills/dependency-upgrade/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [documentation-review](../../skills/documentation-review/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [frontend-quality-review](../../skills/frontend-quality-review/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [git-github-workflow](../../skills/git-github-workflow/evals/evals.json) | 5 | ready (5/5) | not_run | exploratory (case 2 contaminated) | invalid | 1 | [results](results/git-github-workflow.md) |
| [harness-adaptation](../../skills/harness-adaptation/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [implementation-planning](../../skills/implementation-planning/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [parallel-multi-agent](../../skills/parallel-multi-agent/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [quality-hardening](../../skills/quality-hardening/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [reduce-code-size](../../skills/reduce-code-size/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [repository-guidance-authoring](../../skills/repository-guidance-authoring/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [requirements-and-design](../../skills/requirements-and-design/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [review-feedback-resolution](../../skills/review-feedback-resolution/evals/evals.json) | 5 | ready (5/5) | not_run | exploratory (force-injected) | invalid | 1 | [results](results/review-feedback-resolution.md) |
| [rules-and-skills-audit](../../skills/rules-and-skills-audit/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [security-review](../../skills/security-review/evals/evals.json) | 5 | ready (5/5) | not_run | exploratory (force-injected) | invalid | 1 | [results](results/security-review.md) |
| [skill-authoring](../../skills/skill-authoring/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [skill-discovery](../../skills/skill-discovery/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [skill-evaluation](../../skills/skill-evaluation/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [skill-optimizer](../../skills/skill-optimizer/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [skill-reviewer](../../skills/skill-reviewer/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [systematic-debugging](../../skills/systematic-debugging/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |
| [threat-modeling](../../skills/threat-modeling/evals/evals.json) | 5 | designed_only | not_run | not_run | not_run | – | – |

Total: 26 skills, 130 designed cases. Fixtures frozen for 4/26 (the four pilot
skills: code-review, git-github-workflow, review-feedback-resolution,
security-review). Routing measured for 0/26. Execution validated for 0/26 (4
exploratory invalid pilots only).

**Phase 1 (2026-08-16) + follow-up, four pilot skills:** Layer A catalog-routing and
Layer B Docker execution **infrastructure proven** (single-rep smoke on `code-review`;
distinct containers, independent seed copies, baseline received no guidance, free
anonymous model reachable, runner failure correctly rejected). Layer C harness-routing
`not_run` (blocked — no harness selection capture in this CLI). Execution evidence is
validated by `validate_evaluations.py --check-evidence`, which dispatches on an explicit
`evidence_type` field and rejects unknown/malformed evidence rather than skipping it.
No graded n≥3 run published yet, so protocol stays `not_run`. The validator rejects
inflated `valid` claims (verified by negative test). Full efficacy runs require a
graded n≥3 comparison with quoted evidence; see `phase1-environment.md` §6.

## Legend

- `designed_only` — case set exists; no reproducible fixture yet.
- `not_run` — no execution/routing run recorded.
- `exploratory` — historical force-injected pilot; `protocol_status: invalid`; not
  validated proof.
- `invalid` — run cannot be scored as valid (method or environment contamination).
- `limited` — weaker fallback (e.g. instruction-only containment) used knowingly.
- `valid` — meets the corrected protocol (OS-contained or verified harness
  routing; frozen fixtures; evidence retained).

## How to run (corrected)

For each skill, follow `skills/skill-evaluation/SKILL.md` and `RUNBOOK.md`:
build frozen fixtures, run **routing** via real harness selection (capture
selected skill) and **execution** via deliberate activation, keep conditions
independent and leak-free, retain raw evidence, grade with quoted evidence, and
record the full result schema. Do not force-inject the target skill for routing
cases. Do not count force-injected runs as routing proof.
