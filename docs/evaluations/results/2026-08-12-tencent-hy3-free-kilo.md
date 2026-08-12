# Evaluation run — 2026-08-12 — tencent/hy3:free / Kilo

Human-readable companion to [`2026-08-12-tencent-hy3-free-kilo.json`](2026-08-12-tencent-hy3-free-kilo.json) (machine-readable, validated by `scripts/validate_repository.py`).

* **Run ID:** `2026-08-12-tencent-hy3-free-kilo`
* **Timestamp:** `2026-08-12T06:11:00Z`
* **Harness:** `Kilo` `0.1.0`
* **Model:** `tencent/hy3:free` (`provider: tencent`, `reasoning_effort: default`)
* **Baseline:** `no-skill` (same prompts/fixtures/workspace; only the skill's guidance omitted)
* **Skill commit:** `89b0a92`
* **Method:** Each `evals/evals.json` case run twice in a dedicated empty directory (`/tmp/agk-evals-2026-08-12-kilo/<skill>-<id>`) in clean context: WITH-SKILL applies the skill's guidance, BASELINE is a no-skill general agent. Assertions graded with quoted evidence by isolated subagents (one per skill). Raw outputs remain in the ignored workspace.

This is a full fresh run of all 20 validated skills under the Kilo harness (`tencent/hy3:free`, `default` reasoning effort) — one run per condition per model, smoke-level evidence, not a statistical benchmark. Every matching/neighboring/ambiguous (and edge) case showed the skill condition passing more assertions than the baseline where it mattered, supporting `better=true` and `decision=KEEP`.

## Summary

| Skill | Cases | Skill pass / Total | Baseline pass / Total | Better | Decision |
| :--- | ---: | ---: | ---: | :---: | :--- |
| `agent-guidance-maintenance` | 3 | 7/7 | 4/7 | ✓ | `KEEP` |
| `ai-slop-detector` | 3 | 9/9 | 3/9 | ✓ | `KEEP` |
| `architecture-review` | 3 | 9/9 | 1/9 | ✓ | `KEEP` |
| `bootstrap-project` | 3 | 9/9 | 3/9 | ✓ | `KEEP` |
| `catalog-discovery` | 3 | 7/7 | 2/7 | ✓ | `KEEP` |
| `code-review` | 3 | 9/9 | 3/9 | ✓ | `KEEP` |
| `documentation-review` | 3 | 9/9 | 3/9 | ✓ | `KEEP` |
| `git-github-workflow` | 3 | 7/7 | 3/7 | ✓ | `KEEP` |
| `harness-adaptation` | 3 | 9/9 | 2/9 | ✓ | `KEEP` |
| `parallel-multi-agent` | 3 | 8/8 | 1/8 | ✓ | `KEEP` |
| `quality-hardening` | 3 | 9/9 | 2/9 | ✓ | `KEEP` |
| `reduce-code-size` | 3 | 9/9 | 1/9 | ✓ | `KEEP` |
| `rules-and-skills-audit` | 3 | 8/9 | 3/9 | ✓ | `KEEP` |
| `security-review` | 3 | 7/7 | 3/7 | ✓ | `KEEP` |
| `skill-authoring` | 3 | 9/9 | 2/9 | ✓ | `KEEP` |
| `skill-evaluation` | 4 | 12/12 | 8/12 | ✓ | `KEEP` |
| `skill-optimizer` | 3 | 9/9 | 4/9 | ✓ | `KEEP` |
| `skill-reviewer` | 4 | 13/13 | 8/13 | ✓ | `KEEP` |
| `systematic-debugging` | 3 | 8/8 | 3/8 | ✓ | `KEEP` |
| `upstream-contribution` | 3 | 7/7 | 5/7 | ✓ | `KEEP` |
| **Total** | **62** | **174/175** | **64/175** | **20/20** | — |

`Better` means `skill_pass > baseline_pass` for at least one case; `overall_better` is `any(case.better)`. All 20 skills were `overall_better=true`.

## Per-skill detail

### `agent-guidance-maintenance`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 3 | 3/3 | 1/3 | ✓ | (1) skill: explicit --kit-root / AGENT_GUIDANCE_KIT_ROOT / locator / adjacent sibling resolution order vs baseline: clone the kit from GitHub and copy (2) skill: compare installed receipt digests against target files to detect divergence vs baseline: re-copy other skills so they're up to date |
| 2 | neighboring | 2 | 2/2 | 2/2 | – | (1) skill: not proposing any kit adoption/update vs baseline: never mentions the kit (2) skill: closer workflow is security-review vs baseline: security review of application code |
| 3 | ambiguous | 2 | 2/2 | 1/2 | ✓ | (1) skill: receipts dir absent, no adoption receipts to compare vs baseline: directory looks empty (2) skill: will not change files until scope settled and approved vs baseline: propose changes before editing |

**Human review:** Real value concentrated in matching: deterministic source-resolution order + receipt-digest divergence gate the baseline lacks (baseline offers blanket re-copy — overwrite risk). Neighboring adds no lift; ambiguous is slightly verbose but safe.

### `ai-slop-detector`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 4 | 4/4 | 2/4 | ✓ | (1) skill: scoped audit, audit-only mode, no changes vs baseline: broadens into CI/mypy (2) skill: observations vs inferences split vs baseline: style claim as finding |
| 2 | neighboring | 2 | 2/2 | 1/2 | ✓ | (1) skill: code-review/security-review own this, not slop audit vs baseline: executes the review (2) skill: only reviewed the two changed files vs baseline: crept outward with pre-commit scanner |
| 3 | ambiguous | 3 | 3/3 | 0/3 | ✓ | (1) skill: which artifact? won't broaden past what you name vs baseline: cleaned up files it was never pointed at (2) skill: audit-only default vs authorized cleanup vs baseline: no mode distinction (3) skill: changed no file vs baseline: edited unrequested files |

**Human review:** Materially better audits: reproduced a real P1 the green suite hid, tied severity to impact, refused to treat authorship/style as defect. Caveat: no fixtures shipped, so workspaces were synthesized; case 3 edit assertion partly definitional.

### `architecture-review`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 4 | 4/4 | 0/4 | ✓ | (1) skill: inspect source files, docs are claims to verify vs baseline: 'legacy auth is probably a mess' (2) skill: Keep/Evolve/Replace comparison vs baseline: jumps to replace (3) skill: file:line anchors vs baseline: no evidence (4) skill: stops before implementation vs baseline: offers 5-step plan |
| 2 | neighboring | 2 | 2/2 | 1/2 | ✓ | (1) skill: focused changed-code defects belong to code-review vs baseline: never names code-review (2) skill: not launching full architecture review vs baseline: PR bullets |
| 3 | ambiguous | 3 | 3/3 | 0/3 | ✓ | (1) skill: which subsystem, constraints vs baseline: 'rewrite the system' (2) skill: Greenfield not on the table without evidence vs baseline: rewrite as microservices (3) skill: warranted only if simpler change cannot meet real requirement vs baseline: 'modernize' |

**Human review:** Consistently adds decision-framing, source-first evidence discipline, scope gating, hard stop before implementation. Caveat: no real fixture, case 1 passes on methodology intent rather than real anchors.

### `bootstrap-project`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 4 | 4/4 | 1/4 | ✓ | (1) skill: runs inventory_project.py vs baseline: 'suggest adding code-review, security-review' (2) skill: ADD/ADAPT/KEEP_LOCAL/DEFER/SKIP with evidence vs baseline: 'commonly useful' (3) skill: mandatory agent-guidance-maintenance + closes deps vs baseline: copy these folders (4) skill: explicit approval gate vs baseline: ask to go ahead |
| 2 | neighboring | 2 | 2/2 | 0/2 | ✓ | (1) skill: closer workflow is agent-guidance-maintenance vs baseline: adds the security-review skill (2) skill: won't re-run full bootstrap inventory vs baseline: inventory first |
| 3 | ambiguous | 3 | 3/3 | 2/3 | ✓ | (1) skill/baseline: request target root (2) skill: reads existing AGENTS.md/harness before proposing vs baseline: 'what your team workflow looks like' (3) skill/baseline: won't install without approval |

**Human review:** Materially improves matching (inventory + classification + mandatory maintenance skill) and correctly routes kit-update to agent-guidance-maintenance. Ambiguous case: explicitly reading existing AGENTS.md before proposing is the clear win.

### `catalog-discovery`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 3 | 3/3 | 1/3 | ✓ | (1) skill: records source URL, revision, date, license vs baseline: no provenance (2) skill/baseline: read-only, nothing executed/installed (3) skill: disposition table handoff to skill-reviewer vs baseline: no handoff |
| 2 | neighboring | 2 | 2/2 | 1/2 | ✓ | (1) skill/baseline: target adoption not catalog search (2) skill: routes to bootstrap-project vs baseline: no routing |
| 3 | ambiguous | 2 | 2/2 | 0/2 | ✓ | (1) skill: asks scope, clarifies catalog vs target vs baseline: no clarification (2) skill: won't bulk-copy vs baseline: bulk-fetch |

**Human review:** Forces provenance capture, SOURCE_ONLY boundary, correct routing/ambiguity handling the baseline omitted. Soft spot: cautious baseline also avoids executing, so case 1 assertion 2 is weak differentiator.

### `code-review`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 4 | 4/4 | 0/4 | ✓ | (1) skill: anchors changed surface from diff vs baseline: no diff-anchored surface (2) skill: no tests/spec so cannot read contract vs baseline: invents signature claim (3) skill: P0 NameError auth_middleware.py:14 vs baseline: 'Medium-High' no anchors (4) skill: cannot confirm merge readiness vs baseline: 'I'd approve' |
| 2 | neighboring | 2 | 2/2 | 1/2 | ✓ | (1) skill: maps to architecture-review vs baseline: never names workflow (2) skill: won't produce diff-level review for redesign vs baseline: generic rewrite advice |
| 3 | ambiguous | 3 | 3/3 | 2/3 | ✓ | (1) skill/baseline: request specific diff/scope (2) skill: asks review question + contracts vs baseline: omits both (3) skill/baseline: won't evaluate until truth established |

**Human review:** Measurably improves discipline: grounds findings in diff with path:line, refuses invented contract claims, declines to approve, routes redesign to architecture-review. Supplied a fixture diff for case 1 to make matching fair.

### `documentation-review`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 4 | 4/4 | 1/4 | ✓ | (1) skill/baseline: reads README, pyproject, entry point as evidence (2) skill: taxonomy WRONG/STALE/MISSING/ORPHAN/UNVERIFIED/BROKEN vs baseline: none (3) skill: smallest S-gate correction vs baseline: none (4) skill: re-read changed section + verification vs baseline: none |
| 2 | neighboring | 2 | 2/2 | 2/2 | – | (1) skill/baseline: closer workflow is code-review (2) skill/baseline: will not audit docs for a PR |
| 3 | ambiguous | 3 | 3/3 | 0/3 | ✓ | (1) skill: which documents, exact files? vs baseline: none (2) skill: audit vs authorized edit vs baseline: none (3) skill: won't edit until approved vs baseline: edits |

**Human review:** Earns its keep on matching/ambiguous via taxonomy, approval gate, verification contract; neutral on neighboring (correctly declines). Caveat: no fixtures, so grading is workflow-pattern based.

### `git-github-workflow`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 3 | 3/3 | 1/3 | ✓ | (1) skill: git status + confirm base main vs baseline: jumps to checkout -b (2) skill/baseline: atomic conventional commits, no force-push (3) skill: won't push until authorized vs baseline: gives push commands |
| 2 | neighboring | 2 | 2/2 | 1/2 | ✓ | (1) skill/baseline: not a git branching task (2) skill: closer is code-review + security-review vs baseline: offers to review directly |
| 3 | ambiguous | 2 | 2/2 | 1/2 | ✓ | (1) skill: establishes intent + authority (authorize push?) vs baseline: asks intent only (2) skill/baseline: won't force-push/rewrite |

**Human review:** Adds value via explicit approval gating before publishing and correct deferral of diff-review to code/security-review. No unnecessary work or misleading confidence.

### `harness-adaptation`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 4 | 4/4 | 1/4 | ✓ | (1) skill/baseline: identifies harness from session evidence (2) skill: capability profile with discovery paths + skill format vs baseline: none (3) skill: maps rules to canonical owners vs baseline: none (4) skill: first applicable projection strategy vs baseline: none |
| 2 | neighboring | 2 | 2/2 | 1/2 | ✓ | (1) skill: agent-guidance-maintenance owns kit update vs baseline: none (2) skill/baseline: not creating adapter for kit update |
| 3 | ambiguous | 3 | 3/3 | 0/3 | ✓ | (1) skill: requests harness identification evidence vs baseline: none (2) skill: reads AGENTS.md/OPERATING.md/skills before proposing vs baseline: none (3) skill: won't modify target before approval vs baseline: edits |

**Human review:** Forces capability profile, canonical-owner mapping, smallest-projection reasoning, approval gate baseline skips. Routing to agent-guidance-maintenance prevents a wrong adapter.

### `parallel-multi-agent`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 4 | 4/4 | 0/4 | ✓ | (1) skill: verifies authorization to delegate vs baseline: none (2) skill: track matrix with disjoint write scopes vs baseline: none (3) skill: briefs each worker with goal/paths/stop vs baseline: none (4) skill: final gates serially from integrated state vs baseline: none |
| 2 | neighboring | 2 | 2/2 | 1/2 | ✓ | (1) skill: too small to justify overhead vs baseline: none (2) skill/baseline: no delegation for single-file change |
| 3 | ambiguous | 2 | 2/2 | 0/2 | ✓ | (1) skill: requests independent tracks + harness capability vs baseline: none (2) skill: won't delegate without disjoint ownership + plan vs baseline: none |

**Human review:** Materially improves disciplined delegation (authorization, disjoint matrix, serial verification) and suppresses delegation for tiny/ambiguous work. No harmful side effects.

### `quality-hardening`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 4 | 4/4 | 0/4 | ✓ | (1) skill: records baseline counts (5 FAIL/10 runs) vs baseline: ran once, OK (2) skill: adds failing regression test before fix vs baseline: test after fix enshrined defect (3) skill: smallest production fix (no resubmit) vs baseline: lock left double-charge live (4) skill: focused then full gate with counts (20/20) vs baseline: claimed OK, re-run 9/20 fail |
| 2 | neighboring | 2 | 2/2 | 1/2 | ✓ | (1) skill: routes to architecture-review/code-review vs baseline: no named workflow (2) skill/baseline: no QA loop for review request |
| 3 | ambiguous | 3 | 3/3 | 1/3 | ✓ | (1) skill: requests scope + risk boundary vs baseline: which tests only (2) skill: clarifies S/M/high-risk approval gate vs baseline: none (3) skill/baseline: no production edit |

**Human review:** Won 9/9 vs 2/9. Case 1 is load-bearing: baseline got false-green, enshrined double-charge, shipped suite still failing 9/20; test-first + repeat verification exposed the real bugs. Neighboring margin weaker (baseline has no catalog to route to).

### `reduce-code-size`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 4 | 4/4 | 0/4 | ✓ | (1) skill: measures per-file + aggregate LOC first vs baseline: none (2) skill: applies ladder dead→dup→helper→idiom vs baseline: none (3) skill: formatter/linter/tests after each slice vs baseline: none (4) skill: before/after size + tests green vs baseline: none |
| 2 | neighboring | 2 | 2/2 | 1/2 | ✓ | (1) skill: routes to code-review vs baseline: none (2) skill/baseline: no size reduction for review request |
| 3 | ambiguous | 3 | 3/3 | 0/3 | ✓ | (1) skill: requests size objective + target scope vs baseline: none (2) skill: clarifies audit-only vs authorized edit vs baseline: none (3) skill: won't edit without explicit reduction request vs baseline: edits |

**Human review:** Adds real structure (baseline measurement, ordered ladder, per-slice checks, stop conditions) baseline omits; correctly deflects review/ambiguous. Boundary routing sound.

### `rules-and-skills-audit`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 4 | 4/4 | 1/4 | ✓ | (1) skill: discover with rg --files including nested vs baseline: find/glob (2) skill: inventory path/purpose/scope/trigger/deps vs baseline: table of what it does (3) skill: classify duplicate/merge/scope/stale/conflict/improvement vs baseline: vague 'overlap' (4) skill/baseline: smallest reversible change with canonical owner |
| 2 | neighboring | 2 | 2/2 | 1/2 | ✓ | (1) skill: skill-reviewer owns missing content vs baseline: 'add the content' (2) skill/baseline: won't audit structure for content enrichment |
| 3 | ambiguous | 3 | 2/3 | 1/3 | ✓ | (1) skill/baseline: requests repo scope + focus (2) skill: distinguishes structural audit vs content enrichment vs baseline: 'tidy up prose' (3) skill/baseline:FAIL records files read/skipped (none exist at clarification stage) |

**Human review:** Improves routing/structure (taxonomy, rg discovery, canonical-owner framing, reject-sweep boundary) over generic agent. Caveat: case 3 assertion 3 mismatched with clarification-stage scenario; move it to a post-clarification audit case.

### `security-review`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 3 | 3/3 | 1/3 | ✓ | (1) skill/baseline: names trust boundaries (authz, path) (2) skill: confirmed vs hardening separation vs baseline: no separation (3) skill: safe local verification (negative tests) vs baseline: unscoped 'add tests' |
| 2 | neighboring | 2 | 2/2 | 1/2 | ✓ | (1) skill/baseline: won't invent risks from unrelated failure (2) skill: belongs to systematic-debugging vs baseline: 'let's debug' no workflow |
| 3 | ambiguous | 2 | 2/2 | 1/2 | ✓ | (1) skill: requests scope + authority vs baseline: generic tips (2) skill/baseline: won't claim complete assessment |

**Human review:** Adds trust boundaries, confirmed-vs-hardening split, safe-local verification, scope/authority gates, routing away from non-security. Neighboring win modest (baseline already avoids inventing risks).

### `skill-authoring`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 4 | 4/4 | 1/4 | ✓ | (1) skill: writes smallest contract before editing vs baseline: none (2) skill/baseline: creates SKILL.md with correct frontmatter + dir (3) skill: validates routing matching/neighboring/ambiguous vs baseline: none (4) skill: checks every relative link vs baseline: none |
| 2 | neighboring | 2 | 2/2 | 1/2 | ✓ | (1) skill: closer workflow is skill-reviewer vs baseline: none (2) skill/baseline: won't edit skill for review request |
| 3 | ambiguous | 3 | 3/3 | 0/3 | ✓ | (1) skill: requests approved change scope + contract vs baseline: none (2) skill: verifies trigger/owner distinct from existing vs baseline: none (3) skill: won't edit without explicit approval vs baseline: edits |

**Human review:** Materially improves routing discipline, contract-first authoring, approval gating versus baseline. Side effects restricted to approved scope.

### `skill-evaluation`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 4 | 4/4 | 2/4 | ✓ | (1) skill/baseline: clean-context baseline comparison (2) skill: grade every assertion with evidence vs baseline: 'define metrics' no grading (3) skill: human review + context/token cost vs baseline: none (4) skill: non-discriminating/model-variance limits vs baseline: none |
| 2 | neighboring | 2 | 2/2 | 2/2 | – | (1) skill/baseline: routes to skill-authoring (2) skill/baseline: does not invent eval results |
| 3 | ambiguous | 2 | 2/2 | 1/2 | ✓ | (1) skill: requests skill/task examples/baseline/useful-outcome vs baseline: only 'which skill' (2) skill/baseline: won't claim quality from question alone |
| 4 | edge | 4 | 4/4 | 3/4 | ✓ | (1) skill/baseline: dedicated eval root, no unrelated repos (2) skill: exclude/reruns contaminated conditions vs baseline: none (3) skill/baseline: reject post-hoc assertions (4) skill/baseline: rerun all conditions if contract justifies revision |

**Human review:** Improves rigor on matching/edge (clean-context isolation, pre-registered assertions, contamination reruns, cost/variance accounting); neighboring/ambiguous near-ties. Tighten discriminating assertions in those cases.

### `skill-optimizer`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 4 | 4/4 | 1/4 | ✓ | (1) skill: runs guidance_inventory.py baseline vs baseline: none (2) skill: classify exact/near dup, projection bloat, progressive-disclosure miss, routing waste vs baseline: none (3) skill: records owner/replacement/exact change/preserved triggers vs baseline: none (4) skill/baseline: applies only approved findings |
| 2 | neighboring | 2 | 2/2 | 1/2 | ✓ | (1) skill: rules-and-skills-audit owns structural overlap vs baseline: none (2) skill/baseline: routes to rules-and-skills-audit, no inventory |
| 3 | ambiguous | 3 | 3/3 | 2/3 | ✓ | (1) skill: requests root/branch/skipped files vs baseline: none (2) skill/baseline: report-only vs approved edits (3) skill/baseline: won't apply mechanical rewrite without approval |

**Human review:** Wins on all three kinds via measurement, defined taxonomy, correct routing to rules-and-skills-audit. Baseline still handles report-before-edit/authorization, so edge is real but modest.

### `skill-reviewer`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 5 | 5/5 | 2/5 | ✓ | (1) skill/baseline: prohibits executing/installing candidate content (2) skill: requires source revision/date/path/license vs baseline: 'most are MIT, fine' (3) skill: mandatory owner mapping before new skill vs baseline: jumps to Adopt (4) skill: source projects are examples, tested vs unrelated task vs baseline: 'most-starred = polished' (5) skill/baseline: explicit dispositions, report-only |
| 2 | matching | 3 | 3/3 | 3/3 | – | (1) skill/baseline: identifies concrete content gaps, paste-ready additions (2) skill/baseline: no external-source metadata needed for local review (3) skill/baseline: does not edit the skill |
| 3 | neighboring | 2 | 2/2 | 1/2 | ✓ | (1) skill: rules-and-skills-audit owns this vs baseline: performs audit itself (2) skill/baseline: won't start external-source research |
| 4 | ambiguous | 3 | 3/3 | 2/3 | ✓ | (1) skill/baseline: requests source identity (2) skill/baseline: won't copy/execute/install or make unsupported claims (3) skill: application requires later approved skill-authoring step vs baseline: offers to wire up |

**Human review:** 13/13 vs 8/13. Decisive on external-intake provenance, owner mapping, portability testing, neighboring hand-off. Case 2 tied (mostly negative constraints baseline satisfies); strengthen to demand severity-tagged paste-ready drafts.

### `systematic-debugging`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 4 | 4/4 | 2/4 | ✓ | (1) skill/baseline: observed evidence vs hypotheses (2) skill/baseline: reproducible command recorded (3) skill: no speculative fixes stacked vs baseline: 'add a retry for robustness' (4) skill: rejects retry as root-cause mask vs baseline: none |
| 2 | neighboring | 2 | 2/2 | 1/2 | ✓ | (1) skill/baseline: won't invent failure (2) skill: routes to code-review vs baseline: none |
| 3 | ambiguous | 2 | 2/2 | 0/2 | ✓ | (1) skill: requests observed behavior + repro conditions vs baseline: jumps to retry (2) skill: won't claim diagnosis from 'feels flaky' vs baseline: none |

**Human review:** Improves evidence-vs-hypothesis discipline, retry-rejection, routing of non-failure/ambiguous prompts; baseline stacks speculative fixes. Contract and boundaries hold.

### `upstream-contribution`

| ID | Kind | Assertions | Skill | Baseline | Better | Evidence (with-skill) |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | matching | 3 | 3/3 | 1/3 | ✓ | (1) skill: inventories skills + diverged receipts vs baseline: none (2) skill: redacts private paths + provenance vs baseline: 'open a PR' (3) skill/baseline: fork/branch/PR only after approval |
| 2 | neighboring | 2 | 2/2 | 2/2 | – | (1) skill/baseline: not a contribution task (2) skill/baseline: routes to security/code-review |
| 3 | ambiguous | 2 | 2/2 | 2/2 | – | (1) skill/baseline: asks scope + authority before acting (2) skill/baseline: won't auto-push/open PR |

**Human review:** Clearly beats baseline on matching (receipts inventory, provenance, private-data redaction); neighboring/ambiguous handled correctly by both. Add explicit trigger-guard routing security/diff reviews away to strengthen neighboring.

## Relation to validation matrix

Every `✓` in [`docs/evaluations/validation-matrix.md`](../validation-matrix.md) for `tencent/hy3:free` / `Kilo` (`default`) now corresponds to `overall_better=true` and `decision=KEEP` in `2026-08-12-tencent-hy3-free-kilo.json`. The validator checks `better == (skill_pass > baseline_pass)` and `assertions_total` against the committed `evals/evals.json`.

## Limitations

One run per condition per model/harness (`tencent/hy3:free` / Kilo, `default` effort), smoke-level evidence — not a statistical benchmark. Reasoning effort was not explicitly specified and is recorded as `default`. Many evals ship no fixtures, so several subagents synthesized minimal workspaces; results for those cases depend on fixture choice and should be re-run against real fixtures for stronger evidence. `reasoning_effort` (`default` vs other levels) can change results. Several `neighboring`/`ambiguous` cases were near-ties because a capable baseline already routes or asks clarifying questions; consider strengthening those discriminating assertions.

## Files

* Machine-readable: [`2026-08-12-tencent-hy3-free-kilo.json`](2026-08-12-tencent-hy3-free-kilo.json)
* Definitions: `.agents/skills/<name>/evals/evals.json`
* Matrix: [`docs/evaluations/validation-matrix.md`](../validation-matrix.md)
* Raw outputs: ignored workspace `/tmp/agk-evals-2026-08-12-kilo/*` (not committed)
