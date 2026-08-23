# Promptfoo compatibility spike — historical evidence

This directory preserves the completed **M1** Promptfoo compatibility spike as
historical evidence for the **M2** `GO WITH MATERIAL GAPS` decision. It does
**not** merge the spike implementation into AGK.

## Source provenance

| item | value |
| --- | --- |
| spike branch | `spike/promptfoo-compat` (not merged) |
| evidence commit | `217d53f5db7ea01d4fd4fadbefdfe987f663cbb6` |
| frozen baseline | `91ed0155e83d70d0b80a7912d63a2a1c16660b0f` |
| Promptfoo version | `0.122.0` |
| Kilo CLI | `7.4.23` |
| Python / Node | `3.14.6` / `26.7.0` |
| tested model/profile | `kilo/tencent/hy3:free` |
| date | 2026-08-23 |

## Contents

| file | purpose |
| --- | --- |
| `M1-REPORT.md` | Copied verbatim from `experiments/promptfoo/REPORT.md` at `217d53f...` with a provenance header added. Labeled as historical M1 report; M2 corrections do not silently rewrite this record. |
| `KILO-NEXT.md` | Copied verbatim from `experiments/promptfoo/KILO-NEXT.md` at `217d53f...` with a provenance header added. Design note for the preferred thin Kilo provider direction. |
| `evidence-manifest.json` | Inventory of raw `.results/` artifacts with SHA-256 hashes of originals and sanitized copies, plus sanitization notes and retention mode. |
| `sanitized-*.json` | Sanitized copies of the raw Promptfoo result exports (session IDs and absolute local paths stripped). |
| `M2-REVIEW.md` | M2 decision record and gap analysis. |

## Raw evidence retention policy

The original `.results/` artifacts were git-ignored during the spike and therefore
are not present at commit `217d53f...`. Where they survived in the spike worktree,
sanitized representations have been committed here with retained SHA-256 hashes
linking them to the originals. See `evidence-manifest.json` for details.

Original raw artifacts remain **local-only** at:

```
experiments/promptfoo/.results/*.json
```

They contain Kilo session identifiers and absolute host paths and are not
committed. Sanitized copies are committed in this directory.
