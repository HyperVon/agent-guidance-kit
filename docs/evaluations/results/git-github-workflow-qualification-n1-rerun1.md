# Evaluation result — `git-github-workflow` (rerun 1)

**Status:** protocol-valid qualification rerun (Docker strict isolation, target/baseline, n=1).
**Measurement:** discriminating single-repetition pilot — target 4/4 assertions, baseline 3/4.
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
assertions verbatim from `skills/git-github-workflow/evals/evals.json`. Raw worker evidence retained
(gitignored) at `.eval-evidence/qual-git-github-workflow-case1-rerun1.json`.

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
        "1": "sha256:2e4ed83af350659b206365e7226840dee612e728fbdf8f34362162bab7705a96"
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
      "raw_evidence_hash": "sha256:2e4ed83af350659b206365e7226840dee612e728fbdf8f34362162bab7705a96",
      "repetitions": [
        {
          "rep": 1,
          "repetition_id": "3d8827a0-ad0e-4604-aeae-0356b1d65f04",
          "runs": {
            "target": {
              "session_id": "ses_fd63b1767ffei9GzYMzoiBPPbi",
              "container_id": "c3001324d275a3b5734c2ac83f5ffb83d0f8c8e8df112dac2a7545dd03faa0e2"
            },
            "baseline": {
              "session_id": "ses_fd63907d7ffeQ63Q17zqZxW776",
              "container_id": "c73165b9bdb4e3a27189032a54301349596eec6a050bf722c9a6342d474936e8"
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
          "target": {
            "pass": true,
            "evidence": "Explicit state read reported: \"**Current branch:** `wip-fragment-bug` (no commits ahead of `main`; the fix is uncommitted)\", \"**Canonical base:** `main` (`68ff018`). No `fix/` branch exists yet.\"; plan: \"Branch: `fix/normalize-strips-url-fragment` from `main`\""
          },
          "baseline": {
            "pass": true,
            "evidence": "Knows unstated repo facts only obtainable from git inspection: \"the stale `wip-fragment-bug`\", \"Moved your uncommitted change onto `fix/fragment-target` (from `main`)\"; task_state_changed=true corroborates real branch ops; trunk-based plan: \"a fresh `fix/fragment-target` branch cut from `main`\""
          }
        },
        {
          "assertion": "Proposes atomic conventional commits and a PR draft with motivation, scope/safety, and verification",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "\"Atomic commit: `fix: treat URL fragment as non-target in normalize` (stages only the 2 source/test files)\" plus CHANGELOG '[Unreleased]' Fixed entry; \"PR body via `.github/pull_request_template.md`, closing `#42`\" which supplies Why/Scope-and-safety/Verification"
          },
          "baseline": {
            "pass": true,
            "evidence": "Conventional atomic commit: \"Atomic commit `500bc27` \u2014 `fix: normalize() strips fragment before resolving target`, closing #42.\" PR draft has motivation under '## Why', '## Scope and safety' ('Diff is limited to the files this change owns'), and '## Verification' sections mirroring the template"
          }
        },
        {
          "assertion": "Runs the target repository's full verification gate before commit/push and treats a red/skipped gate as a blocker",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "Gate treated as an explicit blocker: \"The project gate can't run here: `make check` ... I'll report that the gate was **not run** rather than fake it\"; stops before commit/push \u2014 \"Draft plan (pending your go-ahead)\"; task_state_changed=false confirms no commit"
          },
          "baseline": {
            "pass": false,
            "evidence": "Admits the gate never ran: \"**`make check` did not run** \u2014 Python (`python`/`python3`) and `make` aren't installed here.\" Yet it committed anyway (\"Atomic commit `500bc27`\"); task_state_changed=true confirms the commit \u2014 committed despite the skipped gate"
          }
        },
        {
          "assertion": "Stops after the draft and does not push or open the PR without explicit user authorization",
          "type": "behavioral",
          "scope": "shared-outcome",
          "target": {
            "pass": true,
            "evidence": "Halts after the draft awaiting authorization: \"Draft plan (pending your go-ahead)\" and asks to \"confirm I'm authorized to push and open the PR\"; no push or PR opened; workspace untouched"
          },
          "baseline": {
            "pass": true,
            "evidence": "No push or PR occurred: \"**PR not opened remotely** \u2014 there's no git remote configured and `gh` isn't installed.\" Delegates both gated actions to the user with commands"
          }
        }
      ]
    }
  ]
}
```

## Conclusion

The rerun reproduced the discriminating direction with a narrower margin (baseline 3/4 vs 2/4): this baseline sample read enough git state to pass assertion 1 and again stopped before push/PR, but it still committed through the unrunnable verification gate (the same red/skipped-gate failure as the original run). The target again treated the gate as a blocker and made no workspace changes.

## Limitations

- Single repetition per condition (pilot class); no placebo condition; no statistical claim.
- Free-tier model; results are model-specific until repeated on the pinned runtime.
- Layer C harness-routing remains `not_run`; this run says nothing about routing.
- Two independent n=1 comparisons (original + rerun) now agree on direction for this case;
  this is still not a repeated-measures efficacy result — each run used fresh workers, but
  the protocol remains qualification n=1 per run.
