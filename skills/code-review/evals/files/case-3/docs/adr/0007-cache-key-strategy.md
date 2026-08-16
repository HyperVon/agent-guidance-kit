# ADR 0007: cache key strategy

Status: accepted (2024.2)
Supersedes: ADR 0004 (flush-on-deploy)

## Context

Before this decision, a schema change to the serialized catalog payload
required flushing the whole Redis namespace on deploy, which produced a
multi-minute cold-cache period and a Postgres load spike.

## Decision

Cache keys embed two versions:

```
cat:{schema_version}:{namespace}:{content_version}:{entity_id}
```

- `schema_version` is a constant in `src/cache/keys.py`, bumped by hand when
  the serialized shape changes.
- `content_version` is read from the `catalog_versions` table and bumped by the
  publish pipeline per namespace.

Old entries are left to expire naturally rather than deleted.

## Consequences

- No flush-on-deploy; a schema bump produces a gradual cold-cache ramp.
- Redis holds up to two generations of a payload during a rollout, costing
  roughly 1.4x namespace memory for the TTL window.
- A forgotten `schema_version` bump serves stale-shaped payloads to new code;
  this is guarded by a serialization round-trip test.
- Key length grew by ~18 bytes, which is not material at current volume.
