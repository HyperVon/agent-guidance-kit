# Catalog expansion evaluation — 2026-08-10

## Scope

This evaluation compared four skills against a no-skill baseline:

- `systematic-debugging`
- `security-review`
- `skill-evaluation`
- `agent-guidance-maintenance`

The first three used the matching, neighboring, and ambiguous cases committed
with their skill directories. The maintenance skill used the same three-case
shape before admission.

## Method

- Harness model: `gpt-5.6-luna`, low reasoning effort.
- Each condition ran in a new ephemeral context from an empty directory.
- User configuration and project rules were disabled.
- Tools were prohibited; answers were limited to 180 words.
- The baseline received only the scenario. The comparison received the same
  scenario plus the complete skill.
- Assertions were graded against the saved output by the parent agent and
  followed by human review.
- Raw model outputs remained in an ignored local evaluation workspace.

One preliminary baseline run was excluded before grading because its working
directory contained unrelated temporary repositories and the agent searched
them. The run was stopped, the isolation fault was corrected, and every scored
run used the empty directory.

This was one run per condition, not a statistical benchmark. Results establish
specific routing defects and smoke-level behavior; they do not establish model-
independent superiority.

## Results

| Skill | Matching | Neighboring | Ambiguous | Decision |
| :--- | :--- | :--- | :--- | :--- |
| `systematic-debugging` | Both conditions satisfied the final assertions and rejected a blind retry | Both routed the maintainability request to code review after the skill gained an explicit scope gate | Both requested concrete failure evidence | `KEEP_PROVISIONAL`: useful standardized procedure, but no advantage over this Luna baseline was demonstrated by the text-only cases |
| `security-review` | Both traced authentication, authorization, and path boundaries safely | Original skill overreached into security checks; revised skill routed the ordinary failing test to systematic debugging | Both established scope and avoided unsupported security claims | `KEEP`: retain the revised routing boundary |
| `skill-evaluation` | Both designed clean-context comparisons; the revised skill additionally codified removal of non-discriminating assertions | Original skill imposed evaluation on an authoring request; revised skill routed it to `skill-authoring` | Both refused to judge quality without inputs and execution | `KEEP`: retain the scope gate and stronger variance guidance |
| `agent-guidance-maintenance` | Baseline covered receipts and approval but omitted portable source resolution; the skill covered all three | Both routed application security review away from kit maintenance | Baseline did not check adoption receipts or source evidence; the skill did | `KEEP`: demonstrated task-specific value over baseline |

## Evidence-backed revisions

1. Replaced the arbitrary three-attempt debugging cutoff with an evidence-
   progress stop condition.
2. Added explicit neighboring-task gates to `systematic-debugging`,
   `security-review`, and `skill-evaluation`.
3. Added model-variance and non-discriminating-assertion guidance to
   `skill-evaluation`.
4. Added `agent-guidance-maintenance` with receipt-aware updates, portable
   source resolution, dependency closure, managed target routing, and a target-
   side validator.

## Remaining evaluation work

- Add a repository fixture for `systematic-debugging`; the current text-only
  cases do not show whether the skill improves trace quality on real source and
  failing tests.
- Repeat decision-sensitive cases across additional supported harnesses and
  models before making portability or statistical claims.
- Expand description-trigger testing when the catalog grows enough for routing
  collisions to become likely.
