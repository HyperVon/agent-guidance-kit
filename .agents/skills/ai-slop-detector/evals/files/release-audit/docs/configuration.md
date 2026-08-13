# Configuration reference

`DISPATCH_RETRY_LIMIT` is passed to the transport and controls how many times
the client retries a temporary failure. `DISPATCH_TIMEOUT_MS` is passed to the
same client as the request timeout. Both values are validated at startup.
