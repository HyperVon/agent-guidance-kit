# Harness adapter contract

The evaluation protocols are harness-neutral. They compare conditions, freeze
the task, verify independent workspaces, and validate assertion evidence. A
harness adapter is responsible only for starting one worker/session and
proving what guidance that worker received.

The adapter is an external command. The evaluator sends one JSON request on
stdin and expects one JSON object on stdout. The command must not use a shell
string supplied by the worker.

## Request

```json
{
  "adapter_protocol": "agent-guidance-kit.harness-adapter/v1",
  "protocol": "regression",
  "condition": "candidate",
  "repetition_id": "...",
  "case_id": 5,
  "natural_task": "...",
  "natural_task_hash": "...",
  "workspace": "/absolute/path/to/independent/workspace",
  "workspace_receipt_path": ".evaluation-runtime/workspace-receipt",
  "attestation_nonce": "...",
  "model": "provider/model-or-runtime-id",
  "guidance": {
    "guidance_id": "code-review",
    "guidance_hash": "sha256:...",
    "guidance_source": "external-runtime",
    "skill_name": "code-review",
    "guidance_path": ".evaluation-runtime/guidance",
    "guidance_content_hash": "sha256:..."
  }
}
```

`guidance` is `null` for a no-skill baseline. For a regression comparison it
is present for both `candidate` and `reference`. The evaluator writes a random
receipt at `workspace_receipt_path` inside every requested workspace; the
adapter must read that file from the requested workspace and return its exact
contents. This binds the response to the workspace that actually hosted the
worker instead of only echoing evaluator-generated IDs. The adapter may copy
or mount the neutral guidance directory into its own native discovery
mechanism, but it must use the same activation procedure for both compared
skill revisions.

## Response

The minimum response for a successful run is:

```json
{
  "run_status": "success",
  "returncode": 0,
  "worker_id": "worker-...",
  "session_id": "session-...",
  "output": "the worker's final output",
  "guidance_probe": "present",
  "guidance_context_probe": "present",
  "activation_verified": true,
  "context_verified": true,
  "guidance_id": "code-review",
  "guidance_hash": "sha256:...",
  "guidance_source": "external-runtime",
  "activation_mechanism": "adapter-defined",
  "workspace_receipt_path": ".evaluation-runtime/workspace-receipt",
  "workspace_receipt": "random-receipt-read-from-requested-workspace",
  "execution_attestation": {
    "protocol": "agent-guidance-kit.execution-attestation/v1",
    "status": "verified",
    "confidence": "independently_verified",
    "verification_mode": "independent",
    "source": "worker",
    "worker_id": "worker-...",
    "session_id": "session-...",
    "nonce": "...",
    "request_hash": "sha256:...",
    "observation_hash": "sha256:...",
    "workspace_receipt_hash": "sha256:...",
    "output_hash": "sha256:...",
    "returncode": 0
  },
  "guidance_path": ".evaluation-runtime/guidance",
  "guidance_content_hash": "sha256:..."
}
```

`worker_id` identifies the independent worker boundary. It may be a container,
sandbox, VM, subprocess, or another harness-specific identifier. A
`container_id` may be included when the adapter uses containers, but it is not
required by the neutral protocol. `adapter_metadata` may contain provider,
model, image, CLI, or version details; the core validator does not interpret
those fields.

Guided responses must identify the guidance by the evaluator-supplied
`guidance_id` and `guidance_hash`, identify the adapter's activation boundary in
`guidance_source`, and report `activation_verified: true` and
`context_verified: true`. These fields describe what guidance was active, not
where a particular harness stores it. `guidance_path`, `skill_name`, and
`guidance_content_hash` remain optional compatibility metadata for legacy
adapters; Kilo-specific paths are never required by this contract. A baseline
response must report the corresponding verification booleans as false (or omit
the guided identity fields).

`workspace_receipt_path` must be the exact neutral path from the request, and
`workspace_receipt` must be the unmodified token read from that path. The
evaluator stores only a hash of the expected token in the repetition metadata;
an adapter that uses a shared or different workspace therefore cannot produce
valid evidence for both conditions.

Successful responses must also include a verified `execution_attestation`.
The evaluator binds that attestation to its nonce and request hash, the returned
worker/session IDs, the workspace receipt, the worker output, and the return
code, probes, and activation mechanism. The `observation_hash` covers those
returned observations as a single canonical binding. The `confidence` level
makes the trust claim explicit:

- `adapter_declared` means the adapter declares the binding and the evaluator
  checks its hashes and request/response consistency. It is valid limited
  evidence, but it is not an independent execution verification.
- `runtime_verified` additionally includes a `runtime_evidence` object bound to
  the worker/session and observation hash. It may support a result-level
  `execution_verified: true` claim when every condition meets this level.
- `independently_verified` requires `verification_mode: "independent"` and is
  the strongest contract level. It may also support `execution_verified: true`.

An adapter must not label copied response fields as a stronger confidence level
than it can support. The result-level `execution_verified: true` claim is
therefore rejected unless every condition's attestation is
`runtime_verified` or `independently_verified`.

## Explicit trust layers

New neutral evidence also records an `attestation_layers` object beside the
condition's flat compatibility fields and `execution_attestation`:

```json
{
  "attestation_layers": {
    "adapter_claims": {
      "guidance_loaded": true,
      "context_loaded": true,
      "execution_completed": true
    },
    "evaluator_verification": {
      "receipt_hash_matches": true,
      "guidance_hash_matches": true,
      "result_schema_valid": true
    },
    "independent_attestation": {
      "available": false,
      "source": null
    }
  }
}
```

The layers have deliberately different meanings:

1. `adapter_claims` preserves what the adapter reported. It is useful
   observation, not independent proof.
2. `evaluator_verification` is recomputed by the evaluator from the returned
   response, evaluator-owned receipt, and expected guidance identity. It means
   the fields are internally consistent; it does not prove an arbitrary
   adapter's worker boundary.
3. `independent_attestation` records the explicitly declared external/runtime
   source when one exists. `available: true` is only allowed to agree with an
   `independently_verified` execution attestation and its non-empty source.

The trust chain is therefore: **adapter says X -> evaluator checks consistency
-> an optional external verifier proves X**. The validator rejects a supplied
layer when it disagrees with the underlying response. Older evidence may omit
`attestation_layers`; that is a compatibility path and does not upgrade its
confidence.

For interoperability, `observation_hash` is the `sha256:` digest of compact,
UTF-8 JSON with sorted keys over these fields: `run_status`, `worker_id`,
`session_id`, `returncode`, `output`, `guidance_probe`,
`guidance_context_probe`, `activation_mechanism`, `workspace_receipt_path`,
and `workspace_receipt`. Missing values are represented as JSON `null`; output
and receipt values are UTF-8 text with replacement for invalid byte sequences.

This contract is harness agnostic, but it has an explicit integration trust
boundary: no universal evaluator can cryptographically prove that an arbitrary
external adapter launched a worker or that a provider's boundary is genuine.
The core therefore verifies the declared bindings and fails closed on missing
or inconsistent attestations; a valid claim still depends on the adapter's
independent worker/harness attestation and its documented implementation.

For a failed invocation, return `run_status: "failed"`, the non-zero
`returncode` when available, and a reason. Failed runs are never evidence.

## Optional harness implementations

The repository's existing Docker/Kilo execution path is retained as an
optional legacy adapter for strict confirmation artifacts. It is not a
requirement of `smoke`, `qualification`, or `regression`, and its fields such
as `.kilo/skills`, `skill_kilo_path`, and `kilo_version` must not be copied into
new harness-neutral result records.

Use the neutral fields above for any other agent harness, model provider,
container runtime, or local test double. If the adapter cannot prove guidance
activation, record the run as limited or invalid rather than inferring it from
file presence alone.
