# Comprehensive online software-engineering skill discovery — working ledger

Status: research complete; the approved recommendations were independently
rewritten into the catalog in a subsequent authoring pass. No external skill
was executed, installed, or copied into `.agents/skills/`.

Date started: 2026-08-13

## Research contract

The objective is to search the online software-engineering and development
skill ecosystem broadly, follow collection and registry links recursively, and
identify portable behaviors that should improve an existing Agent Guidance Kit
skill or justify a distinct candidate. Popularity, stars, forks, and install
telemetry are discovery signals only; they are not quality evidence.

For each serious candidate, the final intake will record the canonical source,
reviewed revision, license, exact path, behavior, current catalog owner,
portable generalization, disposition, and matching/neighboring/ambiguous
forward-test prompts. Unpinned, unlicensed, unsafe, provider-specific, or
insufficiently evidenced material remains a lead or is deferred.

## Discovery topology

The crawl uses these lanes:

1. popularity and install registries (`skills.sh` and directory sites);
2. large curated collections and awesome lists;
3. official vendor/team repositories;
4. independent engineering workflow collections;
5. domain searches for debugging, testing, security, API/schema/migration,
   dependency, CI/release, observability, accessibility, performance,
   architecture/refactoring, and frontend quality.

Collection pages are indexes, not evidence of behavior. Every candidate must
be followed to its origin repository and reviewed there.

## Initial registry and collection frontier

| Source | Current evidence | Research use |
| --- | --- | --- |
| [skills.sh](https://www.skills.sh/) | Install-ranked registry; the current all-time list is led by `find-skills`, Matt Pocock engineering skills, Anthropic/Vercel skills, `agent-browser`, and other high-volume entries. | Popularity seed only; follow each result to origin. |
| [skills.sh documentation](https://www.skills.sh/docs) | States that ranks use anonymous install telemetry and do not guarantee safety or quality. | Quality boundary for interpreting rankings. |
| [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills/tree/bb272b65c8162bed7e1f92d72e9323744ecdb6f5) | Revision `bb272b65c8162bed7e1f92d72e9323744ecdb6f5`; MIT; large curated collection with official-team sections and an explicit untrusted-content warning. | High-signal index and skill-authoring/security guidance source. |
| [mattpocock/skills](https://github.com/mattpocock/skills/tree/84fdeffd12f2ee307994d1eb6feb48173b6e0502) | Revision `84fdeffd12f2ee307994d1eb6feb48173b6e0502`; MIT; high-adoption engineering workflows. | Primary source for debugging, TDD, code review, architecture, triage, and Git guardrails. |
| [linny006/awesome-agent-skills](https://github.com/linny006/awesome-agent-skills/tree/d2b6eb1fbe11bfdb13f2b97256e405ac45f596f0) | Revision `d2b6eb1fbe11bfdb13f2b97256e405ac45f596f0`; MIT; auto-updated GitHub-search directory. | Discovery index only; entries require origin validation. |
| [agentskillexchange/skills](https://github.com/agentskillexchange/skills/tree/049a6459607d377f77ac30efbeb037f80a47904e) | Revision `049a6459607d377f77ac30efbeb037f80a47904e`; source-backed catalog claims no synthetic entries; license still needs confirmation before admission evidence. | Provenance/curation pattern; not a workflow source by itself. |
| [sickn33/agentic-awesome-skills](https://github.com/sickn33/agentic-awesome-skills/tree/1dd6daec9f43c59b5c2082c36abc59c9418b41c6) | Revision `1dd6daec9f43c59b5c2082c36abc59c9418b41c6`; recursive source list and installer-oriented aggregation. | Deduplicate copied entries and trace them to originals. |
| [kodustech/awesome-agent-skills](https://github.com/kodustech/awesome-agent-skills) | Curated software-engineering index organized by frontend, backend, DevOps, testing/QA, security, observability, performance, mobile, infrastructure, tooling, and code review. Revision/license still to pin. | Broad category-coverage check and source-link frontier. |
| [GetBindu/awesome-claude-code-and-skills](https://github.com/GetBindu/awesome-claude-code-and-skills) | Cross-index names large collections including `wshobson/agents`, `addyosmani/agent-skills`, `ECC`, `gstack`, `VoltAgent`, and specialized catalogs. Revision/license still to pin. | Recursive collection frontier; use only to reach origins. |
| [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code/tree/fdc63ce220b1e795c37ab6f05f1bf0149bf4f0bd) | Revision `fdc63ce220b1e795c37ab6f05f1bf0149bf4f0bd`; large Claude Code ecosystem index. License needs direct confirmation. | Index of skills, hooks, commands, agents, and workflows; not a source of copied guidance. |
| [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills/tree/1da55aa810f206d3fe2005e7e3989b15a275d942) | Revision `1da55aa810f206d3fe2005e7e3989b15a275d942`; describes progressive disclosure, official and community collections, and security review. License needs confirmation. | Cross-check official/community engineering skills and authoring patterns. |
| [softaworks/agent-toolkit](https://github.com/softaworks/agent-toolkit/tree/3027f20f3181758385a1bb8c022d4041dfb4de84) | Revision `3027f20f3181758385a1bb8c022d4041dfb4de84`; MIT; includes meta skills for agent-instruction refactoring and skill judging. | Direct source for `skill-optimizer`, `rules-and-skills-audit`, and `skill-reviewer` improvements. |
| [inference-sh/skills](https://github.com/inference-sh/skills/tree/becc25649700d5457772a00e5143e28ccf9e5afa) | Revision `becc25649700d5457772a00e5143e28ccf9e5afa`; tool/vendor collection for image, video, LLM, web search, and SDK skills. | Mostly project-specific/provider-specific; use for exclusion checks. |

## Pinned candidate observations already worth intake

| Origin and revision | Behavior to investigate | Initial mapping |
| --- | --- | --- |
| [Matt Pocock — diagnosing-bugs](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/skills/engineering/diagnosing-bugs/SKILL.md) | Establish a red-capable feedback loop, reproduce/minimize, generate ranked falsifiable hypotheses, instrument one variable, add a seam-level regression, rerun the original reproduction, and clean up diagnostics. | `IMPROVE_EXISTING` → `systematic-debugging`; add tight-loop, hypothesis, performance-baseline, and regression-seam guidance. |
| [Matt Pocock — TDD](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/skills/engineering/tdd/SKILL.md) | Test public interfaces/seams with an independent oracle; avoid implementation-coupled or tautological tests; use vertical slices and red-before-green. | `IMPROVE_EXISTING` → `quality-hardening`; strengthen test-oracle and anti-tautology guidance. |
| [Matt Pocock — code review](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/skills/engineering/code-review/SKILL.md) | Separate specification/contract review from engineering-standards review and freeze a review fixed point. | `IMPROVE_EXISTING` → `code-review`; retain local no-subagent and report-only boundaries. |
| [Matt Pocock — triage](https://www.skills.sh/mattpocock/skills/triage) | Treat issue handling as a state machine with reproduction evidence, needs-info/ready-for-agent/ready-for-human states, and a bounded agent brief. | `NEW_SKILL` candidate → `issue-triage`, or a narrowly scoped addition to `git-github-workflow`; exact source and mutation boundary require review. |
| [Matt Pocock — Git guardrails](https://www.skills.sh/mattpocock/skills/git-guardrails-claude-code) | Block high-risk Git operations through a pre-tool hook and require explicit confirmation for destructive actions. | `IMPROVE_EXISTING` → `git-github-workflow`; exact hook is harness-specific, while the authority contract is portable. |
| [VoltAgent quality guidance](https://github.com/VoltAgent/awesome-agent-skills/blob/bb272b65c8162bed7e1f92d72e9323744ecdb6f5/README.md) | Keep routing metadata compact, use progressive disclosure, avoid absolute paths and blanket tool grants, and treat curated skills as untrusted. | `IMPROVE_EXISTING` → `skill-authoring`, `harness-adaptation`, and `security-review`. |
| [Softaworks — agent-md-refactor](https://github.com/softaworks/agent-toolkit/blob/3027f20f3181758385a1bb8c022d4041dfb4de84/skills/agent-md-refactor/README.md) | Surface contradictions first; retain only universal root instructions; split by topic; flag vague, redundant, default, and stale instructions; verify links and losslessness. | `IMPROVE_EXISTING` → `skill-optimizer` and `rules-and-skills-audit`; do not copy its arbitrary line-count target. |
| [Softaworks — skill-judge](https://github.com/softaworks/agent-toolkit/blob/3027f20f3181758385a1bb8c022d4041dfb4de84/skills/skill-judge/README.md) | Evaluate knowledge delta, activation, structure, progressive disclosure, freedom calibration, pattern fit, and practical usability. | `IMPROVE_EXISTING` → `skill-reviewer`/`skill-optimizer`; compare against local evidence-first and evaluation contracts. |
| [GitHub Awesome Copilot — anti-ui-slop](https://awesome-copilot.github.com/skill/anti-ui-slop/) | Require product-specific UI intent, complete states, responsive/accessibility behavior, real reference evidence, a design contract, and a verification handoff. | `NEW_SKILL` candidate → `frontend-quality-review`; selected anti-slop checks can also enhance `ai-slop-detector`. |
| [Nutlope/Hallmark](https://github.com/nutlope/hallmark/blob/13ac0ec7e148655948100b6396439e481361d690/README.md) | Provides an audit-only UI mode, explicit anti-pattern gates, product-specific structure, and a non-cloning design-study workflow. | Supporting evidence for `frontend-quality-review`; theme generation and automated redesign are project-specific. |
| [Taste Skill](https://github.com/Leonxlnx/taste-skill/blob/e988add20dab0fa97d7a76781c48961c8184288e/README.md) | Uses explicit design-variance, motion, density, redesign-audit, and preflight concepts to counter repetitive AI-generated interfaces. | Supporting evidence for `frontend-quality-review`; opinionated visual dials and image generation are not portable core. |
| [Addy Osmani — code-review-and-quality](https://github.com/addyosmani/agent-skills/blob/main/skills/code-review-and-quality/SKILL.md) | Reviews correctness, readability/simplicity, architecture, security, and performance; checks tests, dependencies, external data, and over-abstraction. | `IMPROVE_EXISTING` → `code-review` and `ai-slop-detector`; verify source revision/license before final intake. |
| [Sentry — security-review](https://github.com/getsentry/skills/blob/main/skills/security-review/SKILL.md) | Routes security review by code context, then loads vulnerability and language/infrastructure references; uses structured findings and explicit needs-verification output. | `IMPROVE_EXISTING` → `security-review`; avoid importing its large framework/language catalog wholesale. |
| [Cloudflare — security-audit-skill](https://github.com/cloudflare/security-audit-skill) | Multi-phase reconnaissance, hunting, independent validation, additive prior-findings memory, and specialized attack-class references. | `IMPROVE_EXISTING` → `security-review`; possible `NEW_SKILL` only if a distinct deep security-audit trigger survives owner/overlap review. |
| [Browserbase — ui-test](https://github.com/browserbase/skills/blob/main/skills/ui-test/SKILL.md) | Plans functional, adversarial, and coverage-gap rounds before browser execution; checks accessibility, responsive behavior, console errors, and visual consistency. | `IMPROVE_EXISTING` → `quality-hardening`; browser orchestration and remote service are project-specific. |
| [Kodus — wcag-audit-patterns](https://github.com/wshobson/agents/tree/main/plugins/accessibility-compliance/skills/wcag-audit-patterns) | Combines automated and manual WCAG 2.2 auditing with remediation guidance. | `NEW_SKILL` candidate → `accessibility-review`; source revision/license and actual behavior still need pinning. |
| [Kodus — command-development lead](https://github.com/anthropics/claude-code/tree/main/plugins/plugin-dev/skills/command-development) | Documents command frontmatter, arguments, file references, restricted tools, validation, error handling, and progressive disclosure. | `PROJECT_SPECIFIC`/possible `IMPROVE_EXISTING` → `harness-adaptation` or `skill-authoring`; Claude Code command syntax is not portable core. |
| [Kodus — agenttrace-session-audit](https://github.com/luoyuctl/agenttrace/tree/master/skills/agenttrace-session-audit) | Audits local agent sessions for cost, tool failures, latency, anomalies, diffs, and CI readiness. | `NEW_SKILL` candidate only for agent-runtime observability; likely outside the current project-local engineering catalog. |

## Safety and quality notes

- Aggregators often repeat the same origin skill. Repeated listings are
  corroboration of discovery or demand, not independent quality evidence.
- Skills that install plugins, invoke remote services, require credentials,
  mutate GitHub/issue trackers, or execute arbitrary scripts remain
  project-specific or require explicit authority boundaries.
- No source was executed or installed during this research.

The first-pass entries below are intentionally conservative. Unpinned or
license-incomplete rows remain discovery leads; they are not admission
recommendations.

## Expanded pinned source frontier (2026-08-13)

These are the additional source repositories and exact files that survived
the first discovery pass. A collection README is recorded when it reveals a
useful taxonomy, quality rule, or linked origin; it is not treated as proof of
the quality of every listed item.

| Source and reviewed revision | License evidence | Exact behavior or source use | Provisional disposition |
| --- | --- | --- | --- |
| [wshobson/agents `c4b82b0`](https://github.com/wshobson/agents/tree/c4b82b0ad771190355eb8e204b1329732a18449a) | MIT in the pinned repository README | 94 plugins, 203 agents, and 175 progressive-disclosure skills; one Markdown source is adapted to five harnesses. Its [portable authoring guide](https://github.com/wshobson/agents/blob/c4b82b0ad771190355eb8e204b1329732a18449a/docs/authoring.md) calls context files tables of contents, keeps detail in references, requires trigger phrases, warns about the Codex 8 KB body cap, and lints harness portability. | `IMPROVE_EXISTING` → `skill-authoring`, `skill-optimizer`, `harness-adaptation`; the generator, model aliases, and adapter scripts are `PROJECT_SPECIFIC`. |
| [wshobson/agents `c4b82b0`, plugin-eval](https://github.com/wshobson/agents/blob/c4b82b0ad771190355eb8e204b1329732a18449a/docs/plugin-eval.md) | Same repository license; exact plugin files may carry their own terms | Static checks, semantic judge, and Monte Carlo evaluation are separated; the repository also checks portability and round-trip generation. | `IMPROVE_EXISTING` → `skill-evaluation`; retain the kit's clean-context and no-untrusted-execution boundary. |
| [affaan-m/ECC `eb497026`](https://github.com/affaan-m/ECC/tree/eb4970265169fec82371c92f615e2e133d875e27) | MIT in the pinned repository metadata | Large catalog with `search-first`, `verification-loop`, `skill-stocktake`, `agent-eval`, `ai-regression-testing`, `contract-first`, and `context-budget`. Individual source files were reviewed rather than accepting the catalog label. | Mostly `IMPROVE_EXISTING`; provider-specific automation and session learning are `DEFER`/`PROJECT_SPECIFIC`. |
| [ECC `search-first`](https://github.com/affaan-m/ECC/blob/eb4970265169fec82371c92f615e2e133d875e27/skills/search-first/SKILL.md) | MIT repository | Checks repository search, package registry, GitHub CLI, and docs/MCP availability; states what was not inspected when a channel is unavailable. | `IMPROVE_EXISTING` → `catalog-discovery`, `systematic-debugging`, and `skill-reviewer`; do not turn it into a universal “always browse” rule. |
| [ECC `verification-loop`](https://github.com/affaan-m/ECC/blob/eb4970265169fec82371c92f615e2e133d875e27/skills/verification-loop/SKILL.md) | MIT | Runs build, type, lint, tests, security, and diff checks and emits a structured readiness report; it is generic in intent but contains JavaScript defaults and a fixed coverage target. | `IMPROVE_EXISTING` → completion/verification contracts across `quality-hardening`, `code-review`, `skill-authoring`, and `git-github-workflow`; do not import its stack assumptions. |
| [ECC `skill-stocktake`](https://github.com/affaan-m/ECC/blob/eb4970265169fec82371c92f615e2e133d875e27/skills/skill-stocktake/SKILL.md) | MIT | Checks overlap, freshness, trigger/scope fit, uniqueness, and usage; produces `Keep`, `Improve`, `Update`, `Retire`, or `Merge` verdicts. | `IMPROVE_EXISTING` → `skill-reviewer` and `rules-and-skills-audit`; the mandatory subagent batches and cached home-directory state are not portable core. |
| [ECC `contract-first`](https://github.com/affaan-m/ECC/blob/eb4970265169fec82371c92f615e2e133d875e27/skills/contract-first/SKILL.md) | MIT | Names consumer/provider owners and one authoritative artifact; defines the smallest useful contract, derives consumer types from it, reviews contract diffs, and verifies both sides against the same contract. | `NEW_SKILL` candidate → `contract-review`/`api-interface-review`, or a bounded addition to `architecture-review` and `code-review`; needs overlap decision. |
| [ECC `context-budget`](https://github.com/affaan-m/ECC/blob/eb4970265169fec82371c92f615e2e133d875e27/skills/context-budget/SKILL.md) | MIT | Accounts for loaded skills, agents, MCP tools, and root instructions to identify context headroom and the largest savings. | `IMPROVE_EXISTING` → `skill-optimizer`; provider-specific token accounting is `PROJECT_SPECIFIC`. |
| [muratcankoylan/Agent-Skills-for-Context-Engineering `6dbe1a1`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/tree/6dbe1a1d868eab51a3bc9011b0f55e2891513e40) | MIT in the pinned repository metadata | `context-degradation` distinguishes poisoning, distraction, confusion, and clash; `context-optimization` says measure before and after, and remove optimization machinery that does not improve the metric; `filesystem-context` recommends durable plans, searchable output files, selective loading, and cleanup. | `IMPROVE_EXISTING` → `skill-optimizer`, `parallel-multi-agent`, `catalog-discovery`; empirical degradation thresholds are research leads, not hard kit constants. |
| [JUNERDD/skills `9f24b324`](https://github.com/JUNERDD/skills/tree/9f24b324863922c394b99014b954033cf36824d4) | MIT per the pinned repository metadata | `thermo-review` is a report-only structural review with recursive candidate coverage, ownership diagnosis, a 350-line inspection trigger, and explicit waivers; `receiving-thermo-review` builds a disposition and behavior-parity ledger before editing; `hack-review` catches impossible-state fallbacks, symptom masking, duplicate abstractions, and boundary bypasses. | `IMPROVE_EXISTING` → `reduce-code-size`, `code-review`, `ai-slop-detector`, and `skill-optimizer`; a new paired review/receiving skill is possible but should not duplicate existing report boundaries. |
| [JUNERDD receiving-code-review](https://github.com/JUNERDD/skills/blob/9f24b324863922c394b99014b954033cf36824d4/skills/receiving-code-review/SKILL.md) | MIT repository | Reconstructs each finding's complete execution chain, verifies current intent and test gaps, and assigns one disposition; its implementation path requires a coding subagent. | `NEW_SKILL` candidate → `review-feedback-reconciliation`; copy only the evidence/disposition behavior, not the mandatory subagent topology. |
| [tech-leads-club/agent-skills `fe318be6`](https://github.com/tech-leads-club/agent-skills/tree/fe318be656b315d5b6f45cf7ea23946b2d0241b0) | README records MIT for the engine and CC-BY-4.0 for maintainer-authored skill content; third-party entries retain their own terms | `tlc-spec-driven` uses Specify → Design → Tasks → Implement with atomic verification criteria and persistent state. | `NEW_SKILL` candidate → `implementation-planning`; attribution and third-party boundaries prohibit wholesale copying. |
| [timwukp/agent-skills-best-practice `8fa50661`](https://github.com/timwukp/agent-skills-best-practice/tree/8fa50661161215b7a409c9c21f274b0b6f916f82) | MIT for repository-authored material; README identifies imported Anthropic examples as Apache-2.0 | API design, CI/CD, database schema design, legacy-code testing, and threat modeling. The legacy-testing skill uses characterization tests before refactoring; threat modeling anchors STRIDE to trust boundaries; API design defines resource/error/pagination/versioning rules. | `IMPROVE_EXISTING` → `quality-hardening`, `security-review`, `architecture-review`; possible `NEW_SKILL` → `schema-migration-safety` only after genericization. |
| [QwenLM/qwen-code review `52cfb189`](https://github.com/QwenLM/qwen-code/blob/52cfb189723325c860e6c732653224e8cb38f900/packages/core/src/skills/bundled/review/SKILL.md) | Apache-2.0 in the pinned repository license | Evidence-led review dimensions include issue fidelity, removed behavior, cross-file tracing, security, reuse, abstraction altitude, sibling consistency, performance-claim reproduction, test efficacy, and attacker/on-call/maintainer perspectives. It fail-closes on unreviewed scope and unverified blockers. | `IMPROVE_EXISTING` → `code-review`, `security-review`, `quality-hardening`; the 1,300-line harness orchestration and CLI submission protocol are `PROJECT_SPECIFIC`. |
| [Trail of Bits skills `304c81a8`](https://github.com/trailofbits/skills/tree/304c81a8cefb6e3c029ebd0d12940ccf0713eccb) | Repository README states CC BY-SA 4.0 | `differential-review`, `fp-check`, `insecure-defaults`, `supply-chain-risk-auditor`, `property-based-testing`, and `spec-to-code-compliance` provide strong review patterns. | `IMPROVE_EXISTING` as independently paraphrased behavior with attribution/legal review; do not copy the skills into this MIT-oriented catalog without resolving the share-alike and per-file terms. |
| [fayerman-source/deslop `928bff32`](https://github.com/fayerman-source/deslop/tree/928bff3298174620abb47664945ae98366855e77) | MIT in the pinned README | Plain-English editing preserves voice, concrete facts, uncertainty, and terms of art; detection names observable patterns without guessing whether text was AI-generated. | `IMPROVE_EXISTING` → `documentation-review` and `ai-slop-detector`; do not make a universal banned-word list or erase deliberate voice. |
| [petergyang/no-ai-slop `d30eddb9`](https://github.com/petergyang/no-ai-slop/tree/d30eddb9e04562234f2070b5ee63ca4649d9a05e) | MIT in the pinned README | Detection reports named patterns and quoted evidence without inferring authorship; editing makes the minimum effective change, preserves voice, avoids invented facts, and reruns its checks. | `IMPROVE_EXISTING` → `ai-slop-detector` and `documentation-review`; content-writing-specific vocabulary rules are optional references, not always-on instructions. |
| [scanaislop/aislop `751121a4`](https://github.com/scanaislop/aislop/tree/751121a4d9b62112f1f127cb84f9a435da02ef26) | MIT in the pinned README | Deterministic code scanner flags narrative comments, swallowed exceptions, hidden fallbacks, unsafe casts, hallucinated imports, duplicate helpers, dead code, TODO stubs, and oversized functions; it supports change-only, JSON/SARIF, safe-fix, and CI modes. | Tool evidence for `IMPROVE_EXISTING` → `ai-slop-detector`, `code-review`, and `quality-hardening`; do not adopt the exact language/tool rules because Kotlin/Java and repository-specific false positives need coverage. |
| [dbachelder/slop-review `86cb4097`](https://github.com/dbachelder/slop-review/tree/86cb4097642b65e11c938a6fe0ee56ba9510ee5f) | MIT in the pinned license, with NOTICE for the upstream port | Provides an explicit user review window for the diff, writes submitted feedback to a file, then addresses comments item by item. | `PROJECT_SPECIFIC` → `harness-adaptation`/`git-github-workflow`; UI/plugin installation and runtime dependencies are not catalog core. |
| [nextlevelbuilder/ui-ux-pro-max-skill `97eb2a20`](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/97eb2a20032f0833e3d317162208a60385b0f96e) | MIT in the pinned README | Generates a product/stack-specific design system with anti-patterns and a pre-delivery checklist covering icons, focus, contrast, reduced motion, and multiple responsive widths; supports a master file with page-specific overrides. | `NEW_SKILL` candidate → `frontend-quality-review`; generated style catalogs and CLI are `PROJECT_SPECIFIC`. |

## Behavior synthesis under the skill-optimizer constraint

The same idea appears across several collections only when it has a stable
failure mode and a distinct decision point. Repetition alone does not justify
another skill. The table below records the smallest plausible owner and the
test that would distinguish a real improvement from a longer prompt.

| Portable behavior | Preferred owner | Why it is not a new generic skill | Forward test required before authoring |
| --- | --- | --- | --- |
| Fresh evidence before a completion/approval claim; show command, exit status, counts, and scope gaps | Cross-cutting contract referenced by `quality-hardening`, `code-review`, `skill-authoring`, and `git-github-workflow` | It is a shared invariant, not a review domain; duplicating it in every body would create drift | Matching: “tests pass; can I say done?”; neighboring: “review only”; ambiguous: “I ran a quick check” — the agent must distinguish fresh evidence from a claim |
| Measure context cost before and after changes; remove optimization machinery with no measured benefit | `skill-optimizer` | Already the catalog skill's central ownership; external sources strengthen measurement and progressive disclosure | Matching: “shrink skill context”; neighboring: “audit overlap”; ambiguous: “make this clearer” — optimizer must not rewrite for style alone |
| Keep entrypoint small, load references just in time, avoid harness-specific tool prose, and flag body-cap risk | `skill-authoring` + `harness-adaptation` | The behavior is packaging/portability policy, not a candidate content skill | Matching: “author a portable skill”; neighboring: “write project rules”; ambiguous: “add a command” — select source skill versus adapter |
| Search local sources and authoritative docs first, report unavailable channels, and do not claim unperformed coverage | `catalog-discovery`, `systematic-debugging`, `documentation-review` | Search is a method used by multiple owners; a universal always-search skill would trigger too often | Matching: “find candidate skills”; neighboring: “debug this local failure”; ambiguous: “what does this API do?” — route source research vs code diagnosis |
| Reconstruct whole execution chains and retain a disposition for every review item | Existing `code-review` plus possible `review-feedback-reconciliation` | Generating a review and receiving feedback are different triggers; the latter is not owned today | Matching: “address these PR comments”; neighboring: “review this diff”; ambiguous: “is this reviewer right?” — produce intake ledger and stop before edits when unverified |
| Check cross-file callers, removed behavior, sibling symmetry, and source-of-truth ownership | `code-review` | Distinct review lenses improve recall but do not need separate routing | Matching: “review changed export”; neighboring: “review one function”; ambiguous: “cleanup duplicate helper” — report callers/owner/evidence, not style preference |
| Verify test independence, characterization behavior before refactor, mutation/property candidates, and red-before-green | `quality-hardening` | TDD, legacy characterization, property tests, and mutation tests are techniques under the test-confidence owner | Matching: “harden tests”; neighboring: “refactor safely”; ambiguous: “add coverage” — prioritize an independent failing oracle over percentage targets |
| Audit false positives and require evidence that a security finding is real before escalating | `security-review` | `fp-check` is a review depth pattern, not a second security domain | Matching: “verify suspected vulnerability”; neighboring: “ordinary bug”; ambiguous: “this looks unsafe” — state evidence, confidence, preconditions, and unresolved uncertainty |
| Classify insecure defaults, fail-open behavior, secrets, supply-chain risk, and trust-boundary threats | `security-review` + `dependency-upgrade` | Same asset/trust-boundary owner; keep dependency provenance and code-flow evidence separate | Matching: “audit defaults/dependencies”; neighboring: “upgrade a version”; ambiguous: “security check” — choose threat flow versus version risk |
| Use an issue/review/structural state machine with `not covered`, `waived`, `disproved`, `confirmed`, and `carried forward` outcomes | `code-review`, `rules-and-skills-audit`, and `skill-reviewer` report contracts | State ledgers are evidence format, not a reason to create a family of narrowly named skills | Matching: “consume a review report”; neighboring: “write a report”; ambiguous: “fix the review” — preserve one disposition per item |
| Treat UI anti-slop as product intent + design contract + all states + responsive/accessibility verification, not as an aesthetic blacklist | New `frontend-quality-review` candidate, with selected checks in `ai-slop-detector` | UI behavior, accessibility, and visual quality are currently under-owned; a focused skill has a distinct trigger | Matching: “review this UI”; neighboring: “build a page”; ambiguous: “make it prettier” — ask for intent/references, inspect states, and report evidence |
| Contract-first API review: consumers/providers, one authoritative schema, error/nullability/versioning compatibility, and generated types | New `contract-review` candidate, or bounded `architecture-review` extension | Public/interface contracts are not currently a distinct owner; avoid duplicating general code review | Matching: “review API contract”; neighboring: “review implementation”; ambiguous: “change response field” — trace both sides and classify breaking impact |
| Release readiness as minimal proof, staged rollout/rollback, monitoring, and cleanup of temporary flags | New `release-readiness` candidate if Git workflow ownership remains too broad | Pre-release decision is a distinct temporal trigger; do not introduce it merely to repeat CI checks | Matching: “can we ship?”; neighboring: “run tests”; ambiguous: “merge this” — require rollback/monitoring and fresh evidence, not a generic checklist |
| Question-driven, privacy-safe observability: name the production question, choose the cheapest useful signal, and avoid telemetry soup | New `observability-hardening` candidate only if production work is in scope | No existing skill owns production signal design; Addy/Swyx patterns are distinct from app security | Matching: “add observability”; neighboring: “debug locally”; ambiguous: “add logs” — identify decision/question and data-sensitivity constraints |
| Spec → design → atomic tasks → acceptance checks before implementation | New `implementation-planning` candidate | Architecture review is recommendation-only and does not own ordinary implementation planning | Matching: “plan this feature”; neighboring: “architecture options”; ambiguous: “start coding” — ask one blocking question at a time and stop at approval boundary |
| Characterize a large/refactor scope with allowlist, checkpoint, handoff, and behavior-parity ledger | `reduce-code-size` + `parallel-multi-agent` | It is a large-change mode, not a default requirement for small changes | Matching: “refactor 80 files”; neighboring: “rename one symbol”; ambiguous: “clean up this module” — activate only above scope/risk threshold |

## Domain coverage and conservative exclusions

### Covered strongly enough for intake

- debugging and error recovery: Matt, Superpowers, Addy, ECC, and Gstack;
- testing and regression confidence: Matt, Superpowers, Timwukp, Trail of
  Bits, Browserbase, ECC, Qwen, and Microsoft test-harness evidence;
- code review and review receipt: Matt, Superpowers, Addy, Trail of Bits,
  Qwen, JUNE, Gstack, and `slop-review`;
- security and supply chain: Trail of Bits, Sentry, Cloudflare, Timwukp,
  Gstack, and vendor collections;
- API/interface/schema/migration: Addy, ECC, Timwukp, Supabase, and Atlas;
- CI/CD, release, and operations: Addy, Swyx, Gstack, Timwukp, GitHub
  Agentic Workflows, and Microsoft;
- observability: Addy, Swyx, Gstack, Simota, and vendor collections;
- accessibility/frontend quality/AI UI slop: Vercel, GitHub Awesome Copilot,
  Wshobson WCAG, Hallmark, Taste Skill, UI UX Pro Max, and anti-ui-slop;
- guidance quality, context, portability, and evaluation: VoltAgent, Wshobson,
  ECC, Murat, Softaworks, Anthropic, and the local optimizer/evaluation skills.

### Recorded but not admitted as portable source

- Large registries and aggregators (`skills.sh`, TheSkillMd, OpenAgentSkill,
  linny, sickn33, Kodus, GetBindu, agentskillexchange, and awesome lists) are
  recursively useful discovery indexes but repeat origins and cannot establish
  behavior or quality on their own.
- Provider/framework packs for React/Next, Expo, Supabase/Postgres, Prisma,
  Vercel, Cloudflare, Azure, AWS, Terraform, Docker, Android/iOS, and specific
  MCP servers are useful when a target project names that stack, but are
  `PROJECT_SPECIFIC` or `DEFER` for this repository-agnostic catalog.
- Browser and native UI tools, external service calls, CLI installers, hooks,
  plugin marketplaces, model routing, cross-model second opinions, and remote
  deployment/canary commands are harness/runtime concerns, not portable skill
  bodies.
- Trail of Bits' CC BY-SA 4.0 repository and Tech Leads Club's mixed licensing
  require attribution and compatibility review before any textual reuse.
- Unlicensed or not-yet-license-verified sources remain leads even when their
  behavior is interesting; this includes the OpenSites and some aggregator
  repositories recorded earlier in this file.

## Optimizer baseline and working conclusion

The local read-only inventory on 2026-08-13 is:

| Measure | Baseline |
| --- | ---: |
| Guidance files | 31 |
| Lines | 2,849 |
| Words | 19,506 |
| Characters | 141,192 |
| Rough token proxy | 35,308 |
| Exact repeated prose blocks over 100 characters | 0 |

This is a size baseline, not an instruction to reduce the catalog. The next
optimizer pass must measure per-skill activation value and routing collisions;
it must not delete safety, approval, provenance, source-of-truth, or
verification language to meet a numerical target.

The current evidence supports a small number of high-confidence improvement
tracks and a few genuinely new candidates. It does not support copying a
large “best skills” pack into this catalog. The final report will rank the
tracks by behavioral delta, trigger distinctness, evidence quality, license
status, implementation cost, and expected context cost, then provide
matching/neighboring/ambiguous probes for each recommended intake.

## Final bounded research sprint (03:49:56 EDT start)

The final sprint followed the remaining domain links and checked additional
official or high-signal origins. The source revision is pinned where a remote
HEAD could be resolved; a discussion or issue is recorded as governance
evidence rather than as reusable skill text.

| Source and reviewed revision | License evidence | Exact behavior or source use | Disposition |
| --- | --- | --- | --- |
| [openai/skills `49f948fa`, security-threat-model](https://github.com/openai/skills/blob/49f948faa9258a0c61caceaf225e179651397431/skills/.curated/security-threat-model/SKILL.md) | License not relied on for reuse in this report; treat official source terms as requiring review before copying | Triggers only on explicit threat-model requests; grounds trust boundaries, assets, attacker capabilities and non-capabilities in repository evidence; separates runtime from CI/dev; asks targeted context questions; checks boundary/entrypoint coverage before reporting. | `NEW_SKILL` candidate → `threat-modeling`, or a clearly bounded extension to `security-review`; its explicit design-time trigger is distinct from vulnerability review. |
| [addyosmani/agent-skills `84fdeffd`, deprecation-and-migration](https://github.com/addyosmani/agent-skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/skills/deprecation-and-migration/SKILL.md) | MIT repository | Requires a working replacement, incremental consumer migration, production proof, zero active old usage, and additive expand/backfill/contract database changes with tested down paths and throttled backfills. | `IMPROVE_EXISTING` → `dependency-upgrade`, `quality-hardening`, and `git-github-workflow`; a standalone migration skill is deferred unless schema work becomes a catalog priority. |
| [UnitOneAI/SecuritySkills `70bc259b`](https://github.com/UnitOneAI/SecuritySkills/tree/70bc259bb01abb3015ad2ad859ad5253cbf0bcab) | License not verified in this sprint | Uses explicit frontmatter for trigger, domain, role, lifecycle phase, and cited frameworks, plus lean entrypoints and on-demand references. | `IMPROVE_EXISTING` → `skill-authoring`/`skill-reviewer`; metadata is a design lead, not a reason to add provider-specific security skills. |
| [agentskills dependency-manifest RFC](https://github.com/agentskills/agentskills/discussions/210) | Discussion/RFC; no skill-text license claim | Proposes a distribution-layer manifest and lockfile with dependency resolution, cycle/conflict/name-collision checks, resolved commits, and integrity digests while keeping `SKILL.md` agent-facing. | `IMPROVE_EXISTING` → catalog governance, `catalog-discovery`, and `skill-authoring`; do not add a manifest without an approved repository design. |
| [openai/skills skill-index proposal](https://github.com/openai/skills/issues/498) | Issue/governance evidence only | Identifies routing cost in large catalogs and proposes a compact index to distinguish overlapping skills without loading every body. | `IMPROVE_EXISTING` → `skill-optimizer`, `rules-and-skills-audit`, and `harness-adaptation`; evaluate a local index only after routing collisions are measured. |
| [jscraik/Agent-Skills `f409eac7`](https://github.com/jscraik/Agent-Skills/tree/f409eac7e21f870253c611ae6026dbd156ec323e) | License not verified in this sprint | Presents doctor/prove/closeout/fold lifecycle commands, explicit eval gates, provenance/manifest ideas, and overlap folding as first-class operations. | `DEFER` as an implementation source; useful corroboration for `skill-evaluation`, `skill-reviewer`, and optimizer lifecycle contracts, but not enough license/source-file evidence for admission. |
| [plannotator/effective-html `d95debba`](https://github.com/plannotator/effective-html/tree/d95debbaef15af1d201fc6c10c77cf92b524a0d6) | License not verified in this sprint | Large, popular collection focused on HTML artifacts, wireframes, prototypes, plans, diagrams, and release-readiness examples. | `PROJECT_SPECIFIC`/`DEFER`; useful for a future artifact/UI workflow, not a general software-engineering skill owner. |

## Final intake ranking

The ranking is based on portable behavioral delta, a distinct trigger, repeated
evidence from independent origins, license/provenance confidence, expected
implementation cost, and optimizer risk. “Improve” means independently
paraphrase and test the behavior under the existing owner; it does not mean
copy the source skill.

### Highest-value improvements to existing owners

| Rank | Owner | Intake behavior | Why it earns priority | Required forward probes |
| ---: | --- | --- | --- | --- |
| 1 | `ai-slop-detector` | Add observable code-slop patterns (hidden fallbacks, swallowed exceptions, invented imports/config, duplicate helpers, dead/TODO stubs, needless abstractions) and UI slop as a product/design-contract/state/accessibility defect. Keep authorship inference and aesthetic bans out. | Strong convergence from AI-slop scanners, no-AI-slop editing, anti-UI-slop, Vercel, and frontend collections; current owner already has the evidence boundary but not the full domain pattern set. | Matching: “audit this AI-generated patch”; neighboring: “review this ordinary diff”; ambiguous: “make this UI less generic.” Require path/evidence/impact and minimum edit or report-only outcome. |
| 2 | `skill-optimizer` | Add context-budget accounting, progressive-disclosure checks, context-poisoning/distraction/confusion/clash diagnosis, and an explicit remove-if-no-measured-benefit rule. | Directly corroborated by ECC, Murat, Wshobson, Softaworks, and the local optimizer contract; this is the user-requested optimization lens with the clearest semantic delta. | Matching: “reduce skill context”; neighboring: “audit overlap”; ambiguous: “make the guidance clearer.” Preserve safety, routing, ownership, approvals, and verification; do not optimize by line count. |
| 3 | `code-review` | Require fixed review point, spec/contract versus standards separation, caller/removed-behavior/sibling tracing, independent test-efficacy checks, coverage ledger, and fail-closed treatment of unverified blockers. | Repeated independently by Matt, Qwen, Trail of Bits, JUNE, Addy, Superpowers, and Gstack; materially improves recall without a new broad review skill. | Matching: “review this PR”; neighboring: “review one function”; ambiguous: “is this reviewer right?” Track every finding and every uncovered area. |
| 4 | `quality-hardening` | Add independent oracles, red-before-green, characterization tests before legacy refactors, property/mutation-test selection heuristics, and fresh verification evidence. | Shared high-value behavior across Matt, Superpowers, Timwukp, Trail of Bits, Qwen, ECC, and Browserbase; current owner can contain it without a TDD skill. | Matching: “harden regression coverage”; neighboring: “refactor safely”; ambiguous: “raise coverage.” Reject tautological tests and percentage-only success. |
| 5 | `skill-authoring` + `harness-adaptation` | Make the entrypoint a compact table of contents; move rare detail to references; require trigger language, source-of-truth ownership, portability checks, body-cap awareness, collision checks, and no absolute/tool-specific prose. | Wshobson, VoltAgent, Anthropic, UnitOne, and the Agent Skills governance discussions converge on this; it reduces routing/context cost while preserving capability. | Matching: “author a portable skill”; neighboring: “write project-local rules”; ambiguous: “add a command.” Verify canonical source and projection separately. |
| 6 | `security-review` | Add false-positive disproof, explicit non-capabilities, insecure-default/fail-open analysis, structured supply-chain signals, and clearer separation from design-time threat modeling. | Trail of Bits, Gstack, Timwukp, UnitOne, and official OpenAI threat-model guidance reinforce the evidence/fail-closed pattern. | Matching: “security review this service”; neighboring: “threat model this API”; ambiguous: “this looks unsafe.” Require asset/boundary/precondition/evidence and unresolved uncertainty. |
| 7 | `systematic-debugging` | Strengthen reproduce/minimize → ranked falsifiable hypotheses → one-variable instrumentation → condition-based waits/performance baselines → seam regression → original reproduction rerun. | Matt, Superpowers, Addy, ECC, and Gstack repeat the loop; it is a high-value refinement with no new trigger. | Matching: “debug this failing test”; neighboring: “implement a feature”; ambiguous: “it seems flaky.” Do not jump to a fix before root cause. |
| 8 | `dependency-upgrade` | Add version-matched advisory evidence and supply-chain indicators: yanked/deprecated/abandoned packages, install scripts/binaries, publisher concentration, provenance, and migration expand/contract safety. | Trail of Bits, Addy, Atlas, Supabase, and ECC add real risk dimensions beyond version bump mechanics. | Matching: “upgrade this dependency”; neighboring: “security-review the repository”; ambiguous: “refresh the lockfile.” Separate confirmed vulnerabilities from informational supply-chain risk. |
| 9 | `reduce-code-size` | Add behavior-characterization, explicit scope allowlists, checkpoints, handoffs, waivers, and behavior-parity evidence; never use line count as the sole success metric. | JUNE, OpenSites, Swyxio, and local optimizer constraints agree; directly guards against “simplification” becoming regression. | Matching: “shrink this module”; neighboring: “rename one symbol”; ambiguous: “clean this up.” Stop when safety/behavior evidence is insufficient. |
| 10 | `skill-evaluation` | Separate static budget/ergonomics checks, semantic judging, clean-context matching/neighboring/ambiguous probes, Monte Carlo/repeated runs, and portability/round-trip checks. | Wshobson, Microsoft, ECC, Jscraik, and the local evaluation skill provide a stronger test model than frontmatter/link validation alone. | Matching: “evaluate this skill”; neighboring: “review its content”; ambiguous: “does this help?” Require a baseline and observable outcome delta. |
| 11 | `catalog-discovery` | Make recursive search explicit: start with popularity/collection indexes, recurse to canonical origins, record dead/unavailable paths, inspect licenses/revisions, deduplicate repeated origins, and never treat popularity as quality. | Directly answers the user’s concern; skills.sh, awesome lists, VoltAgent, and source-first collections show why index-led recursion is necessary but insufficient. | Matching: “find candidate skills”; neighboring: “review one skill”; ambiguous: “what’s popular?” Produce source-backed behavior rows, not a popularity dump. |
| 12 | `documentation-review` + `git-github-workflow` | Add plain-English/minimum-effective-edit rules, no invented claims, release-readiness evidence, rollback/monitoring/flag cleanup, and explicit destructive-operation authority. | Deslop, no-ai-slop, Addy shipping, Gstack, and release-readiness sources extend existing factual-sync and Git boundaries. | Matching: “prepare for release”; neighboring: “update the README”; ambiguous: “can we merge?” Require target-relative readiness and fresh evidence. |

### Genuinely distinct new-skill candidates

| Candidate | Trigger boundary | Portable minimum | Confidence and recommendation |
| --- | --- | --- | --- |
| `frontend-quality-review` | Explicit UI/frontend/UX/accessibility/visual-quality review; not ordinary backend code review or net-new page implementation | Product/user/job intent, design contract and references, hierarchy/navigation, all loading/empty/error/success/disabled/permission states, responsive behavior, keyboard/focus, reduced motion, contrast, performance, and evidence-backed handoff. | **High.** Strongest new owner; avoids forcing `ai-slop-detector` to own all UI quality while still sharing selected anti-slop checks. |
| `threat-modeling` | Explicit threat model, attack-surface, DFD, STRIDE/PASTA/LINDDUN, or abuse-path request; not a generic security review | Repository-grounded components/flows, trust boundaries, assets, attacker capabilities/non-capabilities, realistic abuse paths, likelihood/impact, assumptions/questions, mitigations, and coverage check. | **High.** Current `security-review` explicitly says it is not a substitute for a product-specific threat model; this is a real routing gap. |
| `implementation-planning` | Explicit feature/change plan before implementation; not architecture alternatives or code review | Clarify only blocking unknowns, specify contract and source of truth, design options/tradeoffs, atomic tasks/dependencies, acceptance and verification criteria, approval boundary, and durable handoff. | **Medium-high.** Distinct from recommendation-only `architecture-review`; author only if the catalog wants a general planning owner. |
| `review-feedback-reconciliation` | Explicit request to consume review comments/findings and decide what to do; not generating a fresh code review | Verify each item against current code/intent, trace execution chain, classify confirmed/disproved/duplicate/needs-info/waived/carried, propose bounded changes, and stop before edits unless separately authorized. | **Medium.** Clear trigger gap, but first test whether `code-review` can own it without routing collisions. |
| `release-readiness` | Explicit “ready to merge/handoff/stage/ship/release” decision | Target-relative verdict, fresh evidence, config/secrets/deploy/docs/operations checks, blockers versus caveats, staged rollout/rollback, monitoring, and temporary-flag cleanup. | **Medium.** Consider only if `git-github-workflow` remains overloaded; otherwise add a concise release gate there. |
| `observability-hardening` | Explicit request to add or review production telemetry | Start with an operational question, choose the cheapest useful signal, preserve correlation/async context, handle error sampling, privacy/redaction, cardinality/cost, and verify signal usefulness. | **Medium-low.** Evidence is real but less distinct from debugging/security/operations; defer until production-observability demand is demonstrated. |
| `schema-migration-safety` | Explicit database/schema migration safety or compatibility review | Source-of-truth schema, expand/backfill/contract, old/new compatibility, lock/rewrites/destructive-change analysis, data-dependent checks, rollback/down path, drift, and staged verification. | **Medium-low.** Valuable but provider-specific sources dominate; first genericize under `dependency-upgrade`, `quality-hardening`, and `architecture-review`. |
| `issue-triage` | Explicit issue/PR intake, reproduction and routing, before implementation | State machine, category, repository redundancy check, reproduction evidence, needs-info questions, ready-for-agent/human brief, and no mutation until the maintainer chooses. | **Medium.** Matt provides a clean trigger/state model; consider adding only if GitHub workflow cannot own the distinction. |

### Defer or reject

- **Defer provider/framework packs:** React/Next, Vercel, Supabase/Postgres,
  cloud/IaC, browser, mobile, MCP, and vendor SDK skills. They are useful
  when a target project names the stack, but importing them would create
  catalog breadth and context cost without repository-agnostic evidence.
- **Defer executable workflow packs:** browser control, remote deployment,
  CLI installers, hooks, plugin marketplaces, and cross-model second opinions.
  Their authority, credentials, runtime, and harness assumptions belong in
  adapters or project-specific workflows.
- **Defer legal-risk source text:** Trail of Bits CC BY-SA material and mixed-
  license collections can inform independently written behavior only after
  attribution and compatibility review.
- **Reject popularity-only admission:** a high skills.sh rank, star count,
  or aggregator placement is not evidence that a skill is safe, portable,
  correct, or worth loading.
- **Reject universal “AI detector” claims:** no source justifies inferring
  authorship from style. Keep the existing artifact-defect/evidence boundary.
- **Reject a generic mega-skill:** the combined “engineering best practices”
  packs repeat local owners, increase routing ambiguity, and violate the
  optimizer’s progressive-disclosure objective.

## Recommended approval-gated follow-through

The original research turn made no catalog changes. The approved authoring
pass has now applied the recommended owner improvements and added the two new
skills; dynamic clean-context comparisons remain pending. The smallest next
work packages are:

1. **Evaluation first:** build clean-context matching/neighboring/ambiguous
   probes for `ai-slop-detector`, `skill-optimizer`, `code-review`,
   `quality-hardening`, `security-review`, `skill-authoring`, and the proposed
   `frontend-quality-review`/`threat-modeling` owners.
2. **Apply high-confidence improvements:** author only the approved behavior
   deltas, retaining current report-only, approval, source-of-truth, and
   external-authority boundaries.
3. **Re-run optimizer inventory and routing audit:** compare context cost,
   activation precision, false triggers, and evidence completeness. Keep a
   separate list for intentional reinforcement and thin harness projections.
4. **Decide new owners:** admit `frontend-quality-review` and
   `threat-modeling` first if their probes show materially better routing than
   extensions; defer the remaining new candidates until real demand or
   collision evidence appears.

### Bottom line

The best catalog expansion is not a large import. It is a measured enrichment
of the existing evidence/verification/optimizer spine, plus two likely new
owners—frontend quality review and explicit threat modeling. The AI-slop
material is useful when translated into observable code, documentation, and UI
quality checks; it should strengthen `ai-slop-detector`, not become an
authorship classifier or a cosmetic blacklist.

## Closeout verification

- The report contains 331 lines, 6,094 words, and 54,521 characters; its
  source ledger includes 58 direct Markdown links.
- A trailing-whitespace scan found no matches.
- `git diff --check` passed for tracked changes; this report is currently an
  untracked, user-authorized research artifact, so the scan above was also run
  directly against the file.
- The repository `make check` could not start because this worktree has no
  `.venv/bin/python`. Running `python3 scripts/check.py` also stopped before
  lint because repository Markdown lint setup has not been provisioned. No
  dependency installation was performed during this research-only turn.
- No `.agents/skills/` files were changed; no external skill was executed,
  installed, copied, or admitted.
