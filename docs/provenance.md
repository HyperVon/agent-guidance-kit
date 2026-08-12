# Source provenance

This project was informed by agent-guidance patterns developed and exercised in
two public software projects:

- [HyperVon/new-kraken-rebalancer](https://github.com/HyperVon/new-kraken-rebalancer)
- [HyperVon/rg-helloworld](https://github.com/HyperVon/rg-helloworld)

Portable ideas adapted here include thin harness entrypoints, project-local
precedence, evidence-based artifact review, precise skill contracts,
progressive disclosure, bounded delegation, verification discipline, safe
external-guidance review, provenance, and context/output hygiene.

Project-specific trading rules, product architecture, language ownership,
milestone constraints, credentials, and private/local state are intentionally
excluded.

The reusable skill text in this repository is generalized and rewritten for
this project rather than copied as a universal policy from either source.

## Library research input

The following public sources were reviewed on 2026-08-10 as research input for
the catalog. Their text and bundled assets were not copied or executed.

- [Agent Skills specification and reference tools](https://github.com/agentskills/agentskills)
  (Apache-2.0 for the reference code; documentation licensing varies):
  progressive disclosure, compact skill contracts, and clean-context
  evaluation with observable assertions informed `skill-evaluation` and the
  existing skill-authoring guidance.
- [Anthropic public skills](https://github.com/anthropics/skills) (individual
  skill licenses vary): self-contained skill directories, minimal frontmatter,
  and the distinction between examples and production guarantees informed the
  catalog format and provenance boundary.
- [Superpowers](https://github.com/obra/superpowers) (MIT): systematic
  debugging, evidence before completion, and test-first workflows were
  reviewed. The reusable root-cause and verification ideas were rewritten into
  `systematic-debugging`; its technology-specific and highly prescriptive TDD
  material was not copied.
- [GitHub Awesome Copilot](https://github.com/github/awesome-copilot) (MIT):
  changed-skill detection and dedicated skill linting informed the need for
  focused catalog validation. Its workflow and third-party linter were not
  added as dependencies.
- [OpenAI skills catalog](https://github.com/openai/skills): the repository is
  deprecated and points to the current plugin workflow, so it was treated as
  ecosystem evidence rather than a source for copied skill content.

Disposition: `NEW_SKILL` for systematic debugging, security review, and skill
evaluation; `IMPROVE_EXISTING` for skill-authoring and repository validation;
`DEFER` for technology-specific skills without enough portable evidence.

## First-use adoption evidence

A first adoption of the kit exposed broken links after selective installation,
no persistent maintenance route, and no portable way to rediscover the kit
source. The target's private project details and filesystem paths are not
retained here.

Disposition: `NEW_SKILL` for `agent-guidance-maintenance`;
`IMPROVE_EXISTING` for bootstrap planning, receipt-aware refresh, dependency
closure, managed AGENTS routing, ignored source location, and target-side link
and index validation. Optional neighboring skills remain unlinked; only declared
required dependencies create installation closure.

## 2026-08-12 upstream contribution from rg-helloworld (PR #16)

Adapted from [HyperVon/rg-helloworld](https://github.com/HyperVon/rg-helloworld) at commit `265f780` (retrieved and generalized 2026-08-12, source license Apache-2.0).

- **New portable skills (generalized and rewritten for the kit, not copied verbatim):** `adversarial-pr-review` — parent-orchestrated adaptive adversarial PR review with bounded read-only tracks; `dependency-upgrade` — pinned dependency and lockfile upgrade with security-first triage and risk-grouped verification.
- **Small improvements adopted:** `ai-slop-detector` clarification that emoji, verbosity, formatting, and provider signals are investigation prompts, not evidence of defect or authorship; `code-review` establishment of review truth includes `git status`, complete diff, merge base, and target base; `documentation-review` incremental sync table for post-change documentation updates.
- **Intentionally excluded:** `rg-helloworld`-specific integrity rules, language ownership, milestone sequencing, artifact pipeline (vector glyphs → geometry → SVG → raster → OCR), Kafka/Redis/MinIO/k3d assumptions, and review-surface scripts.

Provenance is recorded here for durability; full triage and disposition (including `PROJECT_SPECIFIC` and `DEFER` for UI, autonomy, and overhaul skills) remains in the PR description.
