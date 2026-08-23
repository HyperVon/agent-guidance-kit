# Evaluation result — `review-feedback-resolution` (rerun 1)

**Status:** protocol-valid qualification rerun (Docker strict isolation, target/baseline, n=1).
**Measurement:** discriminating single-repetition pilot — target 4/4 assertions, baseline 2/4.
This is one observed comparison (`OBSERVED`-class evidence), **not** an efficacy claim: repeats,
a placebo condition, and confirmation remain open per the runbook.

**Why a rerun:** the 2026-08-22 qualification batch ran on a runner whose seed-copy
normalization left the workspace root write/traverse-only for a non-owner container uid
(fixed in commit `c48961b`: coherent `a+rwX` root+descendant normalization, fail-closed
permission errors, and a container-side workspace enumeration probe in the isolation
preflight). The earlier result files are preserved unchanged as historical records of the
pre-fix runner; this rerun re-measures the same frozen cases under the corrected runner.

**Frozen measurement point:** runner head `c48961b` (post-fix); worker image `kilo-eval:local`,
Kilo CLI pinned at 7.4.22 inside the image, model `kilo/tencent/hy3:free` (anonymous free
gateway), reasoning effort high. Conditions ran in distinct containers with distinct sessions
from one hash-verified pristine seed; the target guidance tree was probed present and
hash-matched, the baseline probed absent.

**Grading:** fresh-context blind subagent grader over sanitized outputs (condition labels
randomized to A/B before grading, mapping unmapped after grading); graded against the frozen
assertions verbatim from `skills/review-feedback-resolution/evals/evals.json`. Raw worker evidence retained
(gitignored) at `.eval-evidence/qual-review-feedback-resolution-case1-rerun1.json`.

```result-json
{
  "result_schema_version": 3,
  "evidence_protocol_version": 3,
  "skill": "review-feedback-resolution",
  "evaluation_mode": "execution",
  "method": "docker-isolated",
  "protocol_name_declared": true,
  "case_revision": "sha256:4c763c06399414a4fc693860fb63f10960137963d5d6002c4a513d19fd759555",
  "fixture_revision": "sha256:0ae6eb572f23e18642391b394991342e0370ff725e7dbc042933e67c3c631dc2",
  "target_skill_revision": "sha256:116c178c426f91350cadf18a994a533fc41f2d3f9352d4bb0bfb980c94a53426",
  "runtime": {
    "harness": "kilo",
    "harness_version": "7.4.22",
    "model": "kilo/tencent/hy3:free",
    "reasoning_effort": "high",
    "tool_policy": "--auto permission auto-approval inside container; routing layer --pure",
    "network_policy": "container bridge, no credentials mounted",
    "isolation_method": "docker"
  },
  "protocol": {
    "name": "qualification",
    "status": "valid",
    "tier": "tier-2-strict-isolated",
    "worker_isolation_verified": true,
    "isolation_attestation": {
      "protocol": "agent-guidance-kit.isolation-attestation/v1",
      "status": "verified",
      "verification_mode": "independent",
      "boundary": "os-level",
      "worker_isolation_verified": true,
      "isolation_method": "docker",
      "evidence_hashes": {
        "1": "sha256:416ea0da848966497ddd828ba2a8a5a0a92e9f44da74ded0d2499d5ea844d99c"
      }
    },
    "target_guidance_present": "activation probe confirmed .kilo/skills/review-feedback-resolution/SKILL.md present and hash-matched; context probe present",
    "target_guidance_hash": "sha256:116c178c426f91350cadf18a994a533fc41f2d3f9352d4bb0bfb980c94a53426",
    "target_absent_in_baseline": "boundary probe confirmed no .kilo/skills tree in baseline (skill_probe absent)",
    "baseline_guidance_absent": "boundary probe confirmed no discovery tree in baseline",
    "contamination": "none",
    "natural_task_identical_across_conditions": true,
    "conditions": [
      "target",
      "baseline"
    ],
    "repeats": 1,
    "activation_mechanism": "kilo-command-skill",
    "runtime_treatment_paths": [
      ".kilo/skills"
    ],
    "target_skill_kilo_path": ".kilo/skills/review-feedback-resolution",
    "target_skill_activated": true,
    "target_skill_context_probe": "present"
  },
  "cases": [
    {
      "case_id": 1,
      "natural_task_hash": "sha256:5415c021016183cd08d62c593ba79ec8497349ed2124b758a6fed9ba2da17923",
      "fixture_hash": "sha256:0ae6eb572f23e18642391b394991342e0370ff725e7dbc042933e67c3c631dc2",
      "raw_evidence_hash": "sha256:416ea0da848966497ddd828ba2a8a5a0a92e9f44da74ded0d2499d5ea844d99c",
      "repetitions": [
        {
          "rep": 1,
          "repetition_id": "e6e61828-1d09-4015-9e09-ca982f1fd5ad",
          "runs": {
            "target": {
              "session_id": "ses_fd63f8dccffe5c7HQwyjFM1b1p",
              "container_id": "29e7366e6cd1192d9802b06b173ad703e93b4efe2bb66bf218580f8e168e95a0"
            },
            "baseline": {
              "session_id": "ses_fd63e064affeGvmt1S3s0GIJG0",
              "container_id": "7694a7e431b68e3bb10c3dadf72f259621c59b0873b47e3bf425c3fc3e1b6aea"
            }
          }
        }
      ],
      "outcome": {
        "category": "skill_only_pass",
        "measurement_status": "discriminating",
        "protocol_status": "valid"
      },
      "verdict": {
        "target_pass": true,
        "baseline_pass": false
      },
      "assertions": [
        {
          "assertion": "Records the frozen review context (revision abc1234, branch feature/oidc-login, applicable tests)",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "Dedicated '## Frozen review context' section records 'Revision: abc1234', 'Branch / diff: feature/oidc-login, main...feature/oidc-login', and 'Tests: pytest tests/auth_service_test.py'"
          },
          "baseline": {
            "pass": true,
            "evidence": "Records all three context elements, flagging them as unverifiable: 'I cannot confirm revision abc1234, branch feature/oidc-login, or the range main...feature/oidc-login' and 'The stated applicable tests, tests/auth_service_test.py, do not exist'. Context is recorded (with honest caveat)"
          }
        },
        {
          "assertion": "Assigns exactly one disposition per comment from the defined set (accepted, rejected-with-evidence, already-resolved, duplicate, needs-clarification, deferred)",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "Per-comment table '| # | Comment | Disposition | Evidence / reason | Action |' assigns exactly one defined-set label to each of comments 1-9: deferred, deferred, rejected-with-evidence, needs-clarification, rejected-with-evidence, rejected-with-evidence, rejected-with-evidence, duplicate, already-resolved"
          },
          "baseline": {
            "pass": false,
            "evidence": "Dispositions use free-text labels outside the defined set: '1 - bump 3600s to 24h. Decline.', '3 - Cannot dispose.', '4 - code[:8] collisions. Legitimate.'; only #2 'Defer' and #8 'duplicate of #4' approximate defined labels"
          }
        },
        {
          "assertion": "Uses repository evidence (file/line/contract/test) for any rejected-with-evidence item",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "Code-defect rejected-with-evidence rows cite file/line/contract: C3 'signature check happens upstream at the token endpoint (auth_service.py:41-42)' plus contract citation '(auth_service.py:31-35)'; C6 '(auth_service.py:53-54)'; C7 '(auth_service.py:59)'"
          },
          "baseline": {
            "pass": true,
            "evidence": "Vacuously satisfied (no rejected-with-evidence label used); additionally every decline cites file/line evidence: 'line 43 -> 45 -> OidcToken.subject -> line 56, persisted as the session payload's subject', 'jwks_uri is produced at line 28 and never read'"
          }
        },
        {
          "assertion": "Produces a per-comment table and lists any deferred or needs-clarification items still open",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "Per-comment table covers all 9 rows, followed by '## Open items' explicitly listing 'needs-clarification: Comment 4 (and 8)' and 'deferred: Comment 1 ... and Comment 2' as still-open"
          },
          "baseline": {
            "pass": false,
            "evidence": "No per-comment disposition table (only a line-drift table); dispositions are prose paragraphs; deferred/needs-clarification items never enumerated as still-open"
          }
        }
      ]
    }
  ]
}
```

## Conclusion

The rerun reproduced the discriminating direction but with a narrower margin than the original run (baseline 2/4 vs 0/4): this baseline sample did record the frozen context and grounded its declines in file/line evidence (passing assertions 1 and 3), while still failing the defined disposition taxonomy and the explicit open-items list. The target passed all four assertions again.

## Limitations

- Single repetition per condition (pilot class); no placebo condition; no statistical claim.
- Free-tier model; results are model-specific until repeated on the pinned runtime.
- Layer C harness-routing remains `not_run`; this run says nothing about routing.
- Two independent n=1 comparisons (original + rerun) now agree on direction for this case;
  this is still not a repeated-measures efficacy result — each run used fresh workers, but
  the protocol remains qualification n=1 per run.
