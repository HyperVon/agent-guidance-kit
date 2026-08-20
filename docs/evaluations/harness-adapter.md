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
  "model": "provider/model-or-runtime-id",
  "guidance": {
    "skill_name": "code-review",
    "guidance_path": ".evaluation-runtime/guidance",
    "guidance_content_hash": "sha256:..."
  }
}
```

`guidance` is `null` for a no-skill baseline. For a regression comparison it
is present for both `candidate` and `reference`. The adapter may copy or mount
the neutral guidance directory into its own native discovery mechanism, but it
must use the same activation procedure for both compared skill revisions.

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
  "activation_mechanism": "adapter-defined",
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
