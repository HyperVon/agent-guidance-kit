# Design: caching layer

Status: implemented, in production since 2024.2
Owners: catalog team

## Goals

1. Keep `GET /v1/layers/{id}` under 40ms at p99 for cache hits.
2. Reflect a publish event in client-visible responses within 5s.
3. Survive a Redis outage without returning errors to clients.

## Current shape

Two tiers in front of Postgres:

```
client → api handler → L1 in-process LRU (per pod)
                      → L2 Redis (shared, cluster mode)
                      → Postgres (source of truth)
```

- **L1** is a per-pod LRU with a short TTL (`config/cache.yaml`,
  `namespaces.layer.l1_ttl_seconds: 10`). It absorbs the request-burst pattern
  from tile clients that fetch the same layer many times per second.
- **L2** is Redis with a longer TTL (`l2_ttl_seconds: 900`) and is shared by
  all pods.
- **Invalidation** is push-based: the publish pipeline emits an event, the
  consumer deletes the L2 key and broadcasts a Redis pub/sub message so each
  pod evicts its L1 entry.
- **Warmup** replays the top-N layer ids from the previous hour's access log
  after a deploy.

## Key construction

Keys embed a global schema version and a per-namespace content version so a
schema change does not require a flush. See
`docs/adr/0007-cache-key-strategy.md`.

## Known pain points

1. **Invalidation fan-out is best-effort.** If a pod misses the pub/sub
   message (restart window, network blip), its L1 can serve a stale layer for
   up to `l1_ttl_seconds`. This has caused two incidents (see
   `ops/cache-notes.md`, INC-2210 and INC-2288) where a publish appeared to
   "not take" for a subset of clients.
2. **Two TTLs and one invalidation path.** The effective staleness window is
   the interaction of three settings across two tiers, and it is not obvious
   from any single file what the worst case is.
3. **Warmup competes with live traffic.** Post-deploy warmup issues several
   hundred Postgres reads in the first 30s, which shows up as a latency bump
   on the write path.
4. **Redis outage behavior is untested end to end.** The code path exists
   (`store.py` falls back to Postgres and marks the namespace degraded) but the
   only coverage is a unit test with a stubbed client.
5. **Namespace sprawl.** `config/cache.yaml` has grown to 9 namespaces, three
   of which are served by a single caller.

## Alternatives previously sketched (not evaluated in depth)

- Drop L1 and rely on Redis only, with a read-through client-side coalescer.
- Replace push invalidation with versioned keys only (no deletes), accepting
  extra memory.
- Move to a change-data-capture stream driving cache writes instead of
  invalidations.
- Keep the current layout and only formalize the staleness contract.

No decision has been made on any of these. The team keeps re-opening the
question after each incident without a shared framework for comparing the
options against the 5s publish-visibility requirement.

## Constraints on any future change

- Publish-visibility requirement (5s) is contractual with the mapping partner.
- Redis cluster is shared with two other services; memory growth needs
  platform sign-off.
- The mobile client caches responses for 24h and cannot be updated on our
  release cadence.
