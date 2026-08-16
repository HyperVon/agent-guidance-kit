# Cartogram catalog service

Read-mostly catalog API for the mapping product. Serves layer metadata,
style bundles, and rendered tile manifests to the web and mobile clients.

## Layout

| Path                            | Purpose                                          |
| ------------------------------- | ------------------------------------------------ |
| `src/api/catalog.py`            | Public read endpoints                            |
| `src/cache/store.py`            | Two-tier cache (in-process LRU + Redis)          |
| `src/cache/keys.py`             | Cache key construction and versioning            |
| `src/cache/invalidation.py`     | Invalidation fan-out on publish events           |
| `src/cache/warmup.py`           | Startup and post-deploy warmup                   |
| `src/store/repository.py`       | Postgres-backed source of truth                  |
| `config/cache.yaml`             | Per-namespace TTL and size configuration         |
| `docs/design/caching-layer.md`  | Design of the current caching layer              |
| `docs/adr/0007-cache-key-strategy.md` | Accepted decision on key construction      |
| `ops/cache-notes.md`            | Observed hit rates, latency, and incident history |
| `tests/`                        | pytest suite                                     |

## Local checks

```
pip install -r requirements.txt
PYTHONPATH=src python -m pytest -q
```

## Traffic shape

- ~4.2k req/s peak on `GET /v1/layers/{id}`, ~92% served from cache
- Catalog writes are rare: 20–60 publish events per day, bursty around releases
- Clients tolerate up to 60s of staleness for style bundles, but layer
  geometry must reflect a publish within 5s
