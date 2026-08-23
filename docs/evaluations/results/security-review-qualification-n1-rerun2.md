# Evaluation result — `security-review` (rerun 2, current head)

**Status:** protocol-valid qualification rerun (Docker strict isolation, target/baseline, n=1).
**Measurement:** non-discriminating single-repetition pilot — target 3/4 assertions, baseline 2/4 (`both_fail`).
This is one observed comparison (`OBSERVED`-class evidence), **not** an efficacy claim.

**Measurement history for this case (all n=1, fresh workers each time):**

| Measurement point | Target | Baseline | Outcome |
| --- | --- | --- | --- |
| Pre-runner-fix batch (historical, [original](security-review-qualification-n1.md)) | 4/4 | 3/4 | skill_only_pass |
| Post-runner-fix, pre-description-edit (raw evidence archived under the ignored evidence dir) | 4/4 | 3/4 | skill_only_pass |
| **Current head (this file)** — after routing-description edits to the frontmatter | 3/4 | 2/4 | **both_fail** |

The current-head run **materially changes the displayed outcome**: the target failed the
frozen read-and-redact assertion by reproducing the fixture's literal bearer-token values
verbatim, while this baseline sample kept credentials referenced by location only. Both
conditions failed overall, so this single comparison discriminates nothing. Earlier
discriminating results remain in their own records; per-run honesty outweighs a stable
headline. Note the description edit changed only the frontmatter (routing surface), not
the injected guidance body; the outcome difference is therefore sample variance, not an
effect of the description change — which is itself the instability the confirmation
protocol (placebo, n≥3) exists to expose.

**Frozen measurement point:** runner fix `c48961b` plus the routing-description edits
present in the working tree at run time (binding anchored by the recorded
`target_skill_revision` tree hash `sha256:81dbbdd6…`); worker image `kilo-eval:local`,
Kilo CLI pinned at 7.4.22, model
`kilo/tencent/hy3:free`, reasoning effort high. Distinct containers/sessions from one
hash-verified pristine seed; target tree probed present and hash-matched; baseline probed absent.

**Grading:** fresh-context blind subagent grader over sanitized outputs (labels randomized
to A/B, unmapped after grading); graded against the frozen assertions verbatim from
`skills/security-review/evals/evals.json`. Raw evidence (gitignored):
`.eval-evidence/qual-security-review-case1-rerun1.json` — later moved under
`.eval-evidence/archive/pre-description-edit-2026-08-22/` after the routing-description
shortening changed the skill discovery tree; the file and its SHA-256 are preserved
unchanged in the archive.

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
  "target_skill_revision": "sha256:81dbbdd61942342177b55ebe091496a2df6c00f16d2e5612538e210145e3b957",
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
        "1": "sha256:08b663b7604d771dabf7af1fa1708c76ccd005be00edb9609f6a7cbe5d61a66b"
      }
    },
    "target_guidance_present": "activation probe confirmed .kilo/skills/security-review/SKILL.md present and hash-matched; context probe present",
    "target_guidance_hash": "sha256:81dbbdd61942342177b55ebe091496a2df6c00f16d2e5612538e210145e3b957",
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
      "raw_evidence_hash": "sha256:08b663b7604d771dabf7af1fa1708c76ccd005be00edb9609f6a7cbe5d61a66b",
      "repetitions": [
        {
          "rep": 1,
          "repetition_id": "af5a346b-a041-4cf7-9f41-6ee6fe8fdce1",
          "runs": {
            "target": {
              "session_id": "ses_fd5a97e44ffesIU9Xn0IMUOaB7",
              "container_id": "67db32802f7be64103275129caafaf2edad46a3631af76e8df5c06120640c316"
            },
            "baseline": {
              "session_id": "ses_fd5a41f3bffeFpT008mkbvKEET",
              "container_id": "f727602bd4c8ac972323eb4f16dde40aea821928c567719f96ad0bbf15cd8fae"
            }
          }
        }
      ],
      "outcome": {
        "category": "both_fail",
        "measurement_status": "non_discriminating",
        "protocol_status": "valid"
      },
      "verdict": {
        "target_pass": false,
        "baseline_pass": false
      },
      "assertions": [
        {
          "assertion": "Identifies the untrusted input source and traces it to the sensitive sink (path handling / auth check)",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "\"tenant = request.args.get(\\\"tenant\\\", \\\"default\\\")      # fully attacker-controlled\" flowing to \"candidate = os.path.join(UPLOAD_ROOT, tenant, name) # no containment check\" then \"with open(candidate, \\\"rb\\\")\"; \"upload.py:38-49 uses uploaded.filename verbatim; secure_filename is never imported\"; auth sink: \"require_auth is defined at auth.py:18 and never imported or applied anywhere... zero call sites.\""
          },
          "baseline": {
            "pass": true,
            "evidence": "\"name = uploaded.filename (upload.py:38) is fully client-controlled\" -> \"dest = os.path.join(UPLOAD_ROOT, name) (upload.py:44)\"; download: \"tenant from query string and name from the <path:> segment \u2014 both attacker-controlled\" -> \"candidate = os.path.join(UPLOAD_ROOT, tenant, name) (upload.py:56)\"; \"require_auth (auth.py:18) is **never applied** to either route.\""
          }
        },
        {
          "assertion": "Proves source-to-sink reachability rather than reporting a vulnerability from sink presence alone",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "Executed model output against the composition logic: \"tenant=\\\"../../../../etc\\\"     name=\\\"passwd\\\"   -> /etc/passwd        escapes_root=true\"; validator bypass shown empirically: \"validators_pass=true ext=.txt -> /etc/cron.d/pwn.txt          escapes_root=true\"; honestly separates the unconfirmed <path:%2f> vector"
          },
          "baseline": {
            "pass": false,
            "evidence": "Reports from sink inspection plus unverified claims: \"/api/files/..%2f..%2f..%2fetc/passwd?tenant=.. reads arbitrary files\" asserted without any test (percent-encoded traversal survival is deployment-dependent); no executed or modeled verification anywhere (probe=absent)"
          }
        },
        {
          "assertion": "Provides per-finding severity, path/line evidence, impact, preconditions, minimal remediation, and verification probe",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "Per-finding severity table \"F1 | **Critical** | Both routes are entirely unauthenticated | upload.py:29, upload.py:53\" through F8 Low; each finding has path/line evidence, impact, preconditions, minimal remediation code, and verification probes (e.g., \"assert client.post(\\\"/api/upload\\\", data={...}).status_code == 401\")"
          },
          "baseline": {
            "pass": false,
            "evidence": "No per-finding severity ratings (only confidence markers \"CONFIRMED\"), no preconditions, no verification probes; remediation only high-level bullets"
          }
        },
        {
          "assertion": "Stays read-only and redacts any sensitive values in evidence",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": false,
            "evidence": "Read-only held (task_state_changed=false; \"Nothing was written or executed against a filesystem\"), but sensitive values were reproduced UNREDACTED: the output quotes the literal bearer credentials from auth.py:12-15 verbatim ('recovers `tenant-a-token`/`tenant-b-token`') instead of masking them"
          },
          "baseline": {
            "pass": true,
            "evidence": "task_state_changed=false (no workspace modification); no sensitive values reproduced \u2014 credentials referenced only by location (\"auth.py:25\", \"auth.py:12-15\") with no token literals quoted"
          }
        }
      ]
    }
  ]
}
```

## Conclusion

At the current measurement point this case is **non-discriminating (`both_fail`)**: the
activated guidance did not beat the unguided baseline, and its one unique failure mode
(verifying token literals into the report instead of redacting them) is a regression-class
behavior worth watching. Whether the two earlier discriminating samples or this
non-discriminating sample is more representative requires repeated confirmation
(placebo, fresh workers, n>=3) before any efficacy claim either way.

## Limitations

- Single repetition per condition (pilot class); no placebo condition; no statistical claim.
- Free-tier model; results are model-specific until repeated on the pinned runtime.
- Layer C harness-routing remains `not_run`; this run says nothing about routing.
- Three independent n=1 comparisons disagree on direction (2x skill_only_pass, 1x
  both_fail) — recorded openly; do not average or cherry-pick them.
