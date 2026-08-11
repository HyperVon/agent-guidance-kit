# External skill intake evaluation — 2026-08-10

## Scope and method

This evaluation compared `skill-reviewer` at commit `fab98c2` with the revised
skill and its external-intake reference. It used `gpt-5.6-luna` at low reasoning
effort in fresh ephemeral contexts rooted in an empty directory. User rules were
disabled, tools were prohibited, and responses were limited to 180 words.

One run per condition covered an external-intake request, a neighboring
structural-audit request, and an ambiguous public-repository request. The
committed evaluation definition also includes a local content-review regression
case. Raw outputs were kept only in an ignored local workspace.

## Results

| Case | Previous skill | Revised skill | Decision |
| :--- | :--- | :--- | :--- |
| External intake | Stayed report-only but did not require license, revision, candidate paths, trust controls, or admission dispositions | Required bounded source and license evidence, treated popularity only as discovery input, mapped behavior to owners, and stopped before authoring or installation | Improved |
| Neighboring structural audit | Routed directly to `rules-and-skills-audit` | First revision named the correct owner but briefly claimed the task was in scope; after tightening the `meta` boundary, the rerun routed directly to `rules-and-skills-audit` | Regression found and corrected |
| Ambiguous public repository | Recommended selective review and approval but did not require source identity or licensing evidence | Stopped for the missing URL, publisher, revision, paths, license, and intended behavior; made no unsupported source claims | Improved |

## Decision and limits

`KEEP`: the external-intake mode adds observable provenance, licensing, trust,
catalog-ownership, and admission decisions that the previous skill omitted. The
reference belongs under the existing `skill-reviewer` owner rather than in a
new synonymous skill.

This is smoke-level evidence from one model and one run per condition. It does
not establish model-independent behavior or statistical reliability. Future
catalog-intake work should reuse the same prompts with actual bounded source
fixtures and additional supported harnesses before making broader claims.
