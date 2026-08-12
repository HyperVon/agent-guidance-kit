---
name: documentation-review
description: >-
  Audit and update project documentation against current implementation,
  build/configuration, tests, CI, and authoritative external references when
  needed. Use for documentation audits, documentation sync, stale or incorrect
  claims, runbooks, guides, READMEs, diagrams, or project-local guidance.
---

# Documentation Review

Audit documentation claims against evidence, make the smallest approved
correction, and leave an exact verification record. This skill owns document
truth and document quality; it does not own product-code fixes, test
hardening, architecture decisions, deployment, or remote-system mutations.

## Authority and source of truth

Separate authority for the workflow from evidence for factual claims:

1. The user's request and repository-local rules define scope, permissions, and
   approval requirements.
2. Current implementation, public interfaces, build/configuration, tests,
   generated contracts, CI definitions, and observed behavior are the primary
   evidence for claims about the repository.
3. A named primary external reference may establish an external fact; record
   its source and date when the fact can change.
4. Existing documentation, changelog history, examples, and screenshots are
   evidence to check, not authority over current reality.

When sources disagree, do not guess. Classify the mismatch, identify the
strongest current evidence, state uncertainty, and either correct the document
or defer it. Never broaden a guarantee beyond what the evidence supports.

## Workflow

1. **Scope and inventory.** Identify each document's intended audience and
   purpose. Read the requested documents and only the
   implementation, build/configuration, tests, CI, generated artifacts, or
   primary references needed to verify their claims. Record the paths read.
2. **Map claims to evidence and audience.** Check setup, commands, versions, interfaces,
   behavior, security/safety statements, diagrams, links, screenshots, and
   status claims. Classify each finding as `WRONG`, `STALE`, `MISSING`,
   `ORPHAN`, `UNVERIFIED`, or `BROKEN`. A true statement can still be an
   `ORPHAN` when it is placed for the wrong audience or duplicates a canonical
   owner. Keep a public README focused on understanding, installing, and using
   the project; move detailed exclusions, trust models, and internal rationale
   to design or security documentation unless users need them to avoid an
   immediate misuse.
3. **Report before broad edits.** For each finding, give the document location,
   claim, evidence anchor, impact, smallest correction, and size. Preserve
   unrelated work and do not invent new documentation scope.
4. **Apply the approved slice.** Keep diffs minimal, preserve the document's
   purpose and tone, link to a canonical explanation instead of duplicating
   it, and keep examples generic and secret-free. If a code or test change is
   needed, hand it to the owning skill rather than hiding it in a doc edit.
5. **Verify the saved result.** Re-read changed sections, validate links and
   syntax, render or validate changed diagrams with the repository's supported
   tooling, and run the repository's documented documentation checks. A stale
   visual asset is a separate finding; changing its caption is not visual
   verification.

## Incremental sync after a change set

When the user has just shipped a feature, refactor, or dependency bump and
asks to touch the relevant docs (not a full audit), use this incremental
path instead of the full workflow above:

| Change | Update |
| :----- | :----- |
| Feature, stack, command, or layout | `README.md` (setup, usage, package tree) |
| Architecture, protocol, or milestone order | Architecture doc and `docs/adr/` when the change is architectural |
| Operation or troubleshooting command | Runbook or troubleshooting guide |
| User-facing CLI, UI, or operator workflow | User guide and linked runbook sections |
| Dependency or container version | Version pins, manifests, and lockfile references |

Keep the change minimal: update the one or two owned documents, link to the
canonical source instead of duplicating it, and preserve tone and audience.
For a whole-repository factual audit (missing, wrong, stale), use the full
workflow above.

## Approval gate

Use the repository's size labels when they exist; otherwise use these defaults:

- **S** — One directly evidenced wording, link, or path correction. Apply only
  inside the user's explicit scope and report it.
- **M** — Several documents, a new section, a workflow or compatibility claim,
  or a broad rewrite. Present the exact files, claims, evidence, and revert
  shape; wait for explicit approval.
- **High-risk** — Security, privacy, safety, data handling, migrations,
  compatibility guarantees, operational commands, or claims that could cause
  costly action. Stop for explicit approval, even if the diff is small, and
  include focused evidence and compensating verification.

Do not treat a request to review as permission to edit. Do not create or modify
issues, pull requests, releases, shared infrastructure, or other remote state
automatically.

## Completion contract

Return this report, with no empty or implied fields:

```text
Documentation review
Scope: <requested documents and boundaries>
Sources read: <paths or named authoritative references>
Findings: <count by WRONG/STALE/MISSING/ORPHAN/UNVERIFIED/BROKEN>
Changes: <each changed path and section, or "none">
Verification:
  - <exact check or command> — PASS|FAIL|SKIPPED|BLOCKED; <result/evidence>
  - <link/diagram/render check, if applicable> — PASS|FAIL|SKIPPED|BLOCKED; <result>
Unresolved or deferred: <item, reason, owner/approval needed, or "none">
Changed paths: <exact paths>
```

Report skipped optional tooling as `SKIPPED`, not `PASS`; report unavailable
required evidence as `BLOCKED`. Do not claim completion until every changed
document has been re-read and every applicable check is accounted for.
