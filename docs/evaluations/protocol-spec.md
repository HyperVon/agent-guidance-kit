# Harness-neutral evaluation protocol

This is the canonical contract for new harness-neutral execution and regression
evidence. The [runbook](RUNBOOK.md) explains how to operate a run;
[harness-adapter.md](harness-adapter.md) defines the adapter message shape; and
[result-schema.md](result-schema.md) defines the committed summary format.

## Ownership boundary

The evaluator owns the experiment definition, frozen fixture, natural-task
identity, independent condition workspaces, workspace receipts, task hashes,
revision anchors, comparison semantics, and evidence validation.

The adapter owns starting the worker/session, applying guidance through its
native mechanism, and reporting what the worker received. The core protocol
does not require Kilo, Docker, a provider, a CLI, a container, a VM, or a
particular guidance-discovery directory. Docker/Kilo remains an optional legacy
adapter documented separately.

The evaluator's receipt and internal runtime metadata are evaluator-owned
implementation details. They are not evidence that a particular harness uses
the same filesystem layout. Guidance activation is identified by neutral
identity and adapter evidence, not by a path interpreted by the evaluator.

## Version declarations

New neutral evidence separates three version concepts:

```json
{
  "result_schema_version": 3,
  "evidence_protocol_version": 3,
  "adapter_protocol_version": "agent-guidance-kit.harness-adapter/v1"
}
```

`result_schema_version` describes the JSON result shape. `evidence_protocol_version`
describes the evaluator-owned trust, provenance, and validation rules.
`adapter_protocol_version` identifies the message contract between the evaluator
and one adapter. Version 2 evidence remains readable as a compatibility path;
new runners emit all three declarations.

## Adapter command boundary

The generic runners accept an argv list encoded as JSON:

```bash
python3 scripts/run_harness_eval.py \
  --skill code-review --case-id 5 --protocol qualification \
  --harness-command-json '["python3","path/to/adapter.py"]'
```

The evaluator passes that list directly to `subprocess.run(..., shell=False)`.
Shell metacharacters are ordinary argument data. This prevents shell
interpretation; it is not a sandbox, filesystem boundary, credential barrier,
or arbitrary-code-execution control. Use an externally supplied containment
boundary for untrusted adapters or fixture generators.

## Neutral activation evidence

For a guided condition, the canonical response fields are:

```json
{
  "guidance_identity": "code-review",
  "guidance_hash": "sha256:...",
  "activation_method": "adapter-defined",
  "activation_evidence": {
    "guidance_loaded": true,
    "context_loaded": true
  }
}
```

`guidance_identity` and `guidance_hash` must match the evaluator's requested
bundle. `activation_method` and `activation_evidence` describe the adapter's
mechanism and observation; the evaluator does not interpret their placement.
The former `guidance_id`, `guidance_probe`, `activation_mechanism`, and related
path fields remain readable as compatibility aliases but are not required by
the neutral activation contract.

## Trust and lifecycle

Evidence separates:

1. `attestation_layers.adapter_claims` — what the adapter reports;
2. `attestation_layers.evaluator_verification` — consistency checks recomputed
   from evaluator-owned receipts, identities, hashes, and response shape;
3. `attestation_layers.independent_attestation` — optional external/runtime
   evidence that is independently sourced.

The lifecycle is:

```text
activation_verified -> execution_attested -> isolation_verified -> protocol_valid
```

An adapter claim cannot become proof merely because its hash is internally
consistent. `execution_verified=true` requires strong runtime or independent
execution attestation. `protocol.status: valid` additionally requires the
independent isolation contract; activation is not isolation.

## Reproducibility and failures

Schema v3 regression evidence records exact candidate/reference revisions,
revision-local case anchors, candidate/reference guidance hashes, a case-set
hash, the shared fixture hash, runner version, and `reproduction_status`.
Missing or unresolvable history is `INVALID_REPRODUCTION_ENVIRONMENT`, never a
pass. Historical candidate-controlled generator code is not executed by the
validator.

Failed adapter runs are never valid evidence. The runners normally clean
successful disposable workspaces and seeds. A failed condition automatically
preserves its workspace and seed under the evaluator's ignored temporary area;
`--preserve-failed-artifacts` preserves them even for successful runs. The raw
evidence records the preserved paths for debugging. Remove them only after the
raw evidence and relevant logs have been retained.
