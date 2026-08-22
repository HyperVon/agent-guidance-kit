# Evaluation result — `security-review`

**Status:** protocol-valid qualification run (Docker strict isolation, target/baseline, n=1).
**Measurement:** discriminating single-repetition pilot — target 4/4 assertions, baseline 3/4.
This is one observed comparison (`OBSERVED`-class evidence), **not** an efficacy claim: repeats,
a placebo condition, and confirmation remain open per the runbook.

**Frozen measurement point:** runner head after the seed-copy portability fix (PR #56 merge);
worker image `kilo-eval:local`, Kilo CLI pinned at 7.4.22 inside the image, model `kilo/tencent/hy3:free`
(anonymous free gateway), reasoning effort high. Conditions ran in distinct containers with
distinct sessions from one hash-verified pristine seed; the target guidance tree was probed
present and hash-matched, the baseline probed absent.

**Grading:** fresh-context blind subagent grader over sanitized outputs (condition labels
randomized to A/B before grading, unmapped afterwards); graded against the frozen assertions
verbatim from `skills/security-review/evals/evals.json`. Raw worker evidence retained (gitignored) at
`.eval-evidence/qual-security-review-case1.json`.

```result-json
{
  "result_schema_version": 3,
  "evidence_protocol_version": 3,
  "skill": "security-review",
  "evaluation_mode": "execution",
  "method": "docker-isolated",
  "protocol_name_declared": true,
  "case_revision": "sha256:210f07f7bb209783d8a73cb3856c9fbadf2a4c26bed41a8e83854654c4585a49",
  "fixture_revision": "sha256:55c62272a0861ec264322f11c76af12d4f567e3069800a1c2a48cb6dc60621bb",
  "target_skill_revision": "sha256:2ad8585dd1d54cae02565b29479353bf1e9af4c3045de173e2f934d44d197e99",
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
        "1": "sha256:1a1e6608652c50ed8b2fb6740e7f0dc449a2afb07193ec71481d081260ed1fbc"
      }
    },
    "target_guidance_present": "activation probe confirmed .kilo/skills/security-review/SKILL.md present and hash-matched; context probe present",
    "target_guidance_hash": "sha256:2ad8585dd1d54cae02565b29479353bf1e9af4c3045de173e2f934d44d197e99",
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
    "target_skill_kilo_path": ".kilo/skills/security-review",
    "target_skill_activated": true,
    "target_skill_context_probe": "present"
  },
  "cases": [
    {
      "case_id": 1,
      "natural_task_hash": "sha256:f85e8df649e6880fec27482fd0f0a6c4ce5e7c5488600e7593fbc5216cd7ccbd",
      "fixture_hash": "sha256:55c62272a0861ec264322f11c76af12d4f567e3069800a1c2a48cb6dc60621bb",
      "raw_evidence_hash": "sha256:1a1e6608652c50ed8b2fb6740e7f0dc449a2afb07193ec71481d081260ed1fbc",
      "repetitions": [
        {
          "rep": 1,
          "repetition_id": "6bc4a73f-db8c-423f-80cd-969dbdda69ca",
          "runs": {
            "target": {
              "session_id": "ses_fd7988a02ffeUsJJX2U2fTULiW",
              "container_id": "f4ceac69af95af9fdf889acde5ec54409e65d602fbba7b892494ead1b92f519f"
            },
            "baseline": {
              "session_id": "ses_fd796b66dffeCwNJCXPiIt3cro",
              "container_id": "b4f162d9277d5f1264bc8bfd8fa87055fb48d8bcb9c2757d7ea4902bff33c4f5"
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
          "assertion": "Identifies the untrusted input source and traces it to the sensitive sink (path handling / auth check)",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "PASS: name` comes from `<path:name>` (allows slashes) and `tenant` from query string \u2014 both untrusted"
          },
          "baseline": {
            "pass": true,
            "evidence": "PASS: dest = os.path.join(UPLOAD_ROOT, name)` where `name = uploaded.filename` (client-controlled, `upload.py:38`"
          }
        },
        {
          "assertion": "Proves source-to-sink reachability rather than reporting a vulnerability from sink presence alone",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "PASS: Verified: input `../../../../tmp/evil.pdf` \u2192 `os.path.join` \u2192 `/tmp/evil.pdf` (outside root)"
          },
          "baseline": {
            "pass": true,
            "evidence": "PASS: A request such as `GET /api/files/../../../../etc/passwd` escapes `UPLOAD_ROOT` and the file contents are returned raw"
          }
        },
        {
          "assertion": "Provides per-finding severity, path/line evidence, impact, preconditions, minimal remediation, and verification probe",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "PASS: **Verification probe:** `curl -X POST /api/upload` with no header should return 401, not 201."
          },
          "baseline": {
            "pass": false,
            "evidence": "FAIL: only a generic '### Recommended fixes' section; no per-finding severity/preconditions/verification probe table"
          }
        },
        {
          "assertion": "Stays read-only and redacts any sensitive values in evidence",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "PASS: No files were written or read outside the test harness; traversal was verified by path normalization only."
          },
          "baseline": {
            "pass": true,
            "evidence": "PASS: `current_tenant()` in `auth.py:33`, which is also never used"
          }
        }
      ]
    }
  ]
}
```

## Conclusion

The activated skill guidance outperformed the unguided baseline on this case's shared-outcome
rubric at n=1. The discriminating axis for this case was per-finding severity/precondition/verification-probe completeness.

## Limitations

- Single repetition per condition (pilot class); no placebo condition; no statistical claim.
- Free-tier model; results are model-specific until repeated on the pinned runtime.
- Layer C harness-routing remains `not_run`; this run says nothing about routing.
