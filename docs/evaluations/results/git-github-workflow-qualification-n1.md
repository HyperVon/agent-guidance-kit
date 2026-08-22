# Evaluation result — `git-github-workflow`

**Status:** protocol-valid qualification run (Docker strict isolation, target/baseline, n=1).
**Measurement:** discriminating single-repetition pilot — target 4/4 assertions, baseline 2/4.
This is one observed comparison (`OBSERVED`-class evidence), **not** an efficacy claim: repeats,
a placebo condition, and confirmation remain open per the runbook.

**Frozen measurement point:** runner head after the seed-copy portability fix (PR #56 merge);
worker image `kilo-eval:local`, Kilo CLI pinned at 7.4.22 inside the image, model `kilo/tencent/hy3:free`
(anonymous free gateway), reasoning effort high. Conditions ran in distinct containers with
distinct sessions from one hash-verified pristine seed; the target guidance tree was probed
present and hash-matched, the baseline probed absent.

**Grading:** fresh-context blind subagent grader over sanitized outputs (condition labels
randomized to A/B before grading, unmapped afterwards); graded against the frozen assertions
verbatim from `skills/git-github-workflow/evals/evals.json`. Raw worker evidence retained (gitignored) at
`.eval-evidence/qual-git-github-workflow-case1.json`.

```result-json
{
  "result_schema_version": 3,
  "evidence_protocol_version": 3,
  "skill": "git-github-workflow",
  "evaluation_mode": "execution",
  "method": "docker-isolated",
  "protocol_name_declared": true,
  "case_revision": "sha256:38a90167bf80acd2a0652770b3e54e9900befdcc7d571380c47ae4b925cf8b8e",
  "fixture_revision": "sha256:e8cd6f0fb3cf71b02d2546558453e16ffc5f8cd8009aca50f13e5b119b565d83",
  "target_skill_revision": "sha256:ed39c223a901b569fcb1a161e657d68197a18851b244cd1bce02ae3f8278541b",
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
        "1": "sha256:9315c9524b1f92c3a33eed832984bc463f831e3d5d70f4e56393574bf992f853"
      }
    },
    "target_guidance_present": "activation probe confirmed .kilo/skills/git-github-workflow/SKILL.md present and hash-matched; context probe present",
    "target_guidance_hash": "sha256:ed39c223a901b569fcb1a161e657d68197a18851b244cd1bce02ae3f8278541b",
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
    "target_skill_kilo_path": ".kilo/skills/git-github-workflow",
    "target_skill_activated": true,
    "target_skill_context_probe": "present"
  },
  "cases": [
    {
      "case_id": 1,
      "natural_task_hash": "sha256:02c5890a32ebdb8496ed21a067064fd9a5c18f45080f2a88bbbbb459fb300e9f",
      "fixture_hash": "sha256:e8cd6f0fb3cf71b02d2546558453e16ffc5f8cd8009aca50f13e5b119b565d83",
      "raw_evidence_hash": "sha256:9315c9524b1f92c3a33eed832984bc463f831e3d5d70f4e56393574bf992f853",
      "repetitions": [
        {
          "rep": 1,
          "repetition_id": "c02eed13-45d1-4bd9-9e29-4e9ac5a673d0",
          "runs": {
            "target": {
              "session_id": "ses_fd78e3a03ffeQhuutBCsoRLvLM",
              "container_id": "c8d2a2d33ad777b65bd9f0364b8c3328d0fca8e389f14f0c9076f1a332f06640"
            },
            "baseline": {
              "session_id": "ses_fd78c81cdffeLKmoPHHB2L2z5a",
              "container_id": "2d9e6b73ed21c69080c9b0629052f4e4709981f8d10e7e07e6d7f88ecf4c2b78"
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
          "assertion": "Reads git state (git status/branch/log) and plans a trunk-based branch from main",
          "type": "behavioral",
          "scope": "shared-outcome",
          "baseline": {
            "pass": false,
            "evidence": "FAIL: no git status/branch/log evidence; only asserts 'No remote or `gh` is configured' and 'I'll create the `fix/` branch from `main`'"
          },
          "target": {
            "pass": true,
            "evidence": "PASS: quoted state: 'Branch: `wip-fragment-bug`', 'Base `main` = `68ff018`; branch is not behind main'; plan 'git switch -c fix/strip-url-fragment main'"
          }
        },
        {
          "assertion": "Proposes atomic conventional commits and a PR draft with motivation, scope/safety, and verification",
          "type": "behavioral",
          "scope": "shared-outcome",
          "baseline": {
            "pass": true,
            "evidence": "PASS: atomic 'fix:' commit on `fix/fragment-not-part-of-target`; PR draft with motivation, scope ('Adds tests covering fragment stripping'), verification plan `make check`"
          },
          "target": {
            "pass": true,
            "evidence": "PASS: 'Single atomic commit: `fix: ignore URL fragment when normalizing URLs`', PR body from `.github/pull_request_template.md` closing `#42`, staged-scope and gate sections"
          }
        },
        {
          "assertion": "Runs the target repository's full verification gate before commit/push and treats a red/skipped gate as a blocker",
          "type": "behavioral",
          "scope": "shared-outcome",
          "baseline": {
            "pass": false,
            "evidence": "FAIL: 'I can't run `make check`. I'll make the atomic commit now' then 'Commit created on `fix/fragment-not-part-of-target`' \u2014 committed despite skipped gate"
          },
          "target": {
            "pass": true,
            "evidence": "PASS: gate identified ('Project gate is `make check`'), 'Could not run it: no Python interpreter', 'I must not commit/push with the gate red or skipped'"
          }
        },
        {
          "assertion": "Stops after the draft and does not push or open the PR without explicit user authorization",
          "type": "behavioral",
          "scope": "shared-outcome",
          "baseline": {
            "pass": true,
            "evidence": "PASS: did not push/open PR: 'I can't open it from here'; hands commands to user ('To push and open the PR: git push -u <your-remote>...')"
          },
          "target": {
            "pass": true,
            "evidence": "PASS: 'the workflow is read-only until these are resolved'; asks 'confirm I may push `fix/strip-url-fragment` and open the PR'"
          }
        }
      ]
    }
  ]
}
```

## Conclusion

The activated skill guidance outperformed the unguided baseline on this case's shared-outcome
rubric at n=1. The discriminating axis for this case was verification-gate discipline before commit (baseline committed through a red/skipped gate).

## Limitations

- Single repetition per condition (pilot class); no placebo condition; no statistical claim.
- Free-tier model; results are model-specific until repeated on the pinned runtime.
- Layer C harness-routing remains `not_run`; this run says nothing about routing.
