# Cache operations notes

## Steady-state numbers (last 30 days)

| Metric                        | Value        |
| ----------------------------- | ------------ |
| L1 hit rate (`layer`)         | 63%          |
| L2 hit rate (`layer`)         | 29%          |
| Source reads (`layer`)        | 8%           |
| p50 / p99 cached response     | 4ms / 37ms   |
| p99 source-read response      | 210ms        |
| Redis memory, catalog prefixes | 3.1 GB      |
| Publish events per day        | 20–60        |

## Incidents

### INC-2210 — publish not visible on two pods

A layer publish was visible on 6 of 8 pods. Two pods had restarted during the
pub/sub broadcast and kept serving the previous payload until the L1 TTL
expired. Client impact: ~9s of mixed responses.

### INC-2288 — same signature, larger blast radius

A release rolled pods while a burst of 14 publishes was in flight. Mixed
responses lasted ~40s for the `style` namespace, which has a 30s L1 TTL.
The mapping partner opened a ticket citing the 5s publish-visibility term.

### INC-2402 — Redis cluster failover

A cluster failover took the L2 tier out for 90s. The service stayed up and
served from Postgres at p99 240ms; no client errors. The degraded-namespace
signal fired correctly.

## Open operational questions

- Should the warmup budget be capped so post-deploy Postgres load stops
  colliding with the write path?
- Do the `attribution`, `legend`, `glyphs`, and `sprites` namespaces need
  separate configuration, given they share one caller and one TTL profile?
- Is the current staleness window compatible with the 5s partner term during a
  rolling deploy, or only in steady state?
