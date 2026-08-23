# Frontmatter description bloat inventory (follow-up candidates)

Generated 2026-08-22 by scanning every `skills/*/SKILL.md` frontmatter. Descriptions are
routing metadata for an LLM router, not human-facing mini-documentation: target roughly
25–45 words (~≤60 with a routing reason), core job + strongest trigger + minimal boundary
vs the nearest neighbor. This file is an optimization backlog, not a record of changes;
no catalog text was modified to produce it except the three descriptions already reworked
in this PR (`code-review`, `security-review`, `architecture-review`).

Current distribution: median 48 words across 26 skills; 2 exceed 60 words.

## Priority candidates

| Skill | Words | Chars | Likely bloated | Neighbor distinction clear? | Recommendation |
| --- | ---: | ---: | --- | --- | --- |
| skill-reviewer | 79 | 594 | yes | yes (3-way vs rules-and-skills-audit / documentation-review) | Compress to ~40 words; keep the three-way boundary, drop the trailing restatement of scope |
| repository-guidance-authoring | 61 | 446 | borderline | yes (vs skill-authoring / harness-adaptation / documentation-review) | Trim to ~45; the triple do-not chain can become one contrast clause |
| documentation-review | 58 | 463 | mild | yes (vs skill-reviewer) | Drop the capability enumeration (runbooks/guides/READMEs/diagrams); keep source-truth-vs-prose-depth distinction |
| frontend-quality-review | 58 | 425 | mild | yes (vs code-review) | Move the browser-automation safety clause to the body; keep review-vs-implement boundary |
| codebase-orientation | 57 | 400 | mild | yes (vs architecture-review / documentation-review / implementation-planning) | Acceptable as-is; optional light trim |

## Within budget — no action needed unless evidence appears

implementation-planning (56), requirements-and-design (55), threat-modeling (55),
harness-adaptation (54), parallel-multi-agent (54), skill-evaluation (54),
review-feedback-resolution (52), skill-discovery (48), adversarial-pr-review (47),
ai-slop-detector (47), code-review (45, this PR), reduce-code-size (44),
security-review (44, this PR), quality-hardening (43), dependency-upgrade (38),
systematic-debugging (38), git-github-workflow (37), rules-and-skills-audit (35),
architecture-review (34, this PR), skill-optimizer (33), skill-authoring (29).

## Rules for any future optimization pass

1. Extract the ownership contract from the SKILL.md body first; never shorten by deleting
   a routing distinction.
2. One contrast clause against the nearest neighbor beats an enumeration of do-nots.
3. Safety/workflow prose belongs in the body unless it changes routing.
4. After any edit: rerun the owning confusion set(s) plus the unchanged holdout once;
   never tune against the holdout.
5. Re-run `python3 scripts/run_catalog_routing_eval.py` for affected sets and compare
   confusion matrices before and after; report regressions rather than iterating.
