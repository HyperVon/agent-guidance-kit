# Service boundary contract

- Guest access is disabled by default and missing credentials fail closed.
- No fallback credential may authorize a request.
- Upstream failures remain failures; a successful empty response must not hide
  an authorization, certificate, or transport error.
- Dependency advisories require local reachability and version evidence before
  they are called confirmed vulnerabilities.
