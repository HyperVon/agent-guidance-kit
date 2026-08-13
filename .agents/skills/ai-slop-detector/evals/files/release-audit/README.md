# Dispatch Console

Dispatch Console sends fulfillment requests from a small operations panel.
The current release supports the desktop and 390px mobile layouts, retries a
temporary transport failure, and exposes configuration through environment
variables.

## Development

```sh
make check
```

The check covers the unit suite and the repository lint step. The latest
release notes say all checks are green before deployment.

## Configuration

* `DISPATCH_RETRY_LIMIT` controls the maximum number of transport attempts.
* `DISPATCH_TIMEOUT_MS` controls the request timeout used by the dispatch
  client.
