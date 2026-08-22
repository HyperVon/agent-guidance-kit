# Evaluation result — `review-feedback-resolution`

**Status:** protocol-valid qualification run (Docker strict isolation, target/baseline, n=1).
**Measurement:** discriminating single-repetition pilot — target 4/4 assertions, baseline 0/4.
This is one observed comparison (`OBSERVED`-class evidence), **not** an efficacy claim: repeats,
a placebo condition, and confirmation remain open per the runbook.

**Frozen measurement point:** runner head after the seed-copy portability fix (PR #56 merge);
worker image `kilo-eval:local`, Kilo CLI pinned at 7.4.22 inside the image, model `kilo/tencent/hy3:free`
(anonymous free gateway), reasoning effort high. Conditions ran in distinct containers with
distinct sessions from one hash-verified pristine seed; the target guidance tree was probed
present and hash-matched, the baseline probed absent.

**Grading:** fresh-context blind subagent grader over sanitized outputs (condition labels
randomized to A/B before grading, unmapped afterwards); graded against the frozen assertions
verbatim from `skills/review-feedback-resolution/evals/evals.json`. Raw worker evidence retained (gitignored) at
`.eval-evidence/qual-review-feedback-resolution-case1.json`.

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
        "1": "sha256:a7c73d7f6d5427831f1dfc372d5e4f83f53f256f73d4ada16cdecf6db44f6309"
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
      "raw_evidence_hash": "sha256:a7c73d7f6d5427831f1dfc372d5e4f83f53f256f73d4ada16cdecf6db44f6309",
      "repetitions": [
        {
          "rep": 1,
          "repetition_id": "553dec6a-79a3-4e43-b4eb-531f9b487c1b",
          "runs": {
            "target": {
              "session_id": "ses_fd791b413ffe6orDKpEsw8D6s6",
              "container_id": "db6311a9c73dc2bca2f2c1b1a004445b8f78a6cb579921e0d4b7a7c3fea1dabc"
            },
            "baseline": {
              "session_id": "ses_fd790c76fffeO8yU7ZS4RmjHYY",
              "container_id": "88c1ef40c32df885287691d9a47e0b06811faa6488690cb37716790389277f72"
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
            "evidence": "PASS: Frozen review context\u2026 Revision: abc1234\u2026 Branch/diff: feature/oidc-login\u2026 Tests: pytest tests/auth_service_test.py"
          },
          "baseline": {
            "pass": false,
            "evidence": "FAIL: revision abc1234, branch feature/oidc-login, and applicable tests never recorded"
          }
        },
        {
          "assertion": "Assigns exactly one disposition per comment from the defined set (accepted, rejected-with-evidence, already-resolved, duplicate, needs-clarification, deferred)",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "PASS: 9 rows each with exactly one defined category: #1\u2013#7 'rejected-with-evidence', #8 'duplicate', #9 'already-resolved'"
          },
          "baseline": {
            "pass": false,
            "evidence": "FAIL: disposition column is free text ('Product-policy preference', 'Perf optimization'); only #8 'Duplicate' uses a defined category; 7 of 9 have none"
          }
        },
        {
          "assertion": "Uses repository evidence (file/line/contract/test) for any rejected-with-evidence item",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "PASS: rejections anchored to repo: 'auth_service.py:12', 'auth_service.py:38-40', 'auth_service.py:53-54', 'auth_service.py:59', plus quoted contracts"
          },
          "baseline": {
            "pass": false,
            "evidence": "FAIL: de facto rejects 8 comments with no file/line/test anchors anywhere; only bare names (`exchange_code_for_token`)"
          }
        },
        {
          "assertion": "Produces a per-comment table and lists any deferred or needs-clarification items still open",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "PASS: per-comment markdown table plus explicit 'Open / deferred items' section ('None deferred', #8 folded into #4)"
          },
          "baseline": {
            "pass": false,
            "evidence": "FAIL: per-comment table present, but no explicit open-items list; deferred status appears only in passing ('#1 deferred to product')"
          }
        }
      ]
    }
  ]
}
```

## Conclusion

The activated skill guidance outperformed the unguided baseline on this case's shared-outcome
rubric at n=1. The discriminating axis for this case was frozen-context disposition taxonomy with repository-anchored evidence and an explicit open-items list.

## Limitations

- Single repetition per condition (pilot class); no placebo condition; no statistical claim.
- Free-tier model; results are model-specific until repeated on the pinned runtime.
- Layer C harness-routing remains `not_run`; this run says nothing about routing.
