# Authentication contract

- Identity comes from a verified `Authorization: Bearer <session-token>` value;
  request headers must not be accepted as identity or role assertions.
- Any authenticated user may access ordinary reports. Only an authenticated
  administrator may access administrator routes.
- Missing or invalid credentials return `401`; a valid identity without route
  permission returns `403`.
- The middleware must not trust caller-controlled role or identity headers.
