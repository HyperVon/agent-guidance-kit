# Source provenance

This project was informed by agent-guidance patterns proven in two public
software projects:

- [HyperVon/new-kraken-rebalancer](https://github.com/HyperVon/new-kraken-rebalancer)
- [HyperVon/rg-helloworld](https://github.com/HyperVon/rg-helloworld)

Portable ideas adapted here include thin harness entrypoints, project-local
precedence, evidence-based artifact review, precise skill contracts,
progressive disclosure, bounded delegation, verification discipline, safe
external-guidance review, provenance, and context/output hygiene.

Project-specific trading rules, product architecture, language ownership,
milestone constraints, provider catalogs, credentials, model availability,
runtime configuration, and private/local state are intentionally excluded.

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
`DEFER` for technology-specific skills and provider/runtime workflows.
