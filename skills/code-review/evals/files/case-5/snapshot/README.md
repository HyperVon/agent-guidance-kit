# Reporting API

Internal reporting service for tenant transaction records. Standard library
only: no third-party runtime or test dependencies.

## Layout

| Path                 | Purpose                                        |
| -------------------- | ---------------------------------------------- |
| `app/router.py`      | Request/response plumbing and dispatch         |
| `app/config.py`      | Environment configuration                      |
| `app/store.py`       | Record source (in-memory for local runs)       |
| `app/auth.py`        | API key checks                                 |
| `app/reports.py`     | Summary endpoints                              |
| `app/main.py`        | Route registration                             |
| `docs/api.md`        | Endpoint contract                              |
| `tests/`             | unittest suite                                 |

## Checks

```
make test
```

or directly:

```
python3 -m unittest discover -s tests -t .
```
