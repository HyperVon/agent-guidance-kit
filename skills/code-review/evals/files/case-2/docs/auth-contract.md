# Authentication contract

Applies to `service/auth.py` and `service/token.py`. Approved by the platform
security review board; changes require a fresh review.

## Bearer tokens

1. Every non-public route requires a bearer token in `Authorization`.
2. Tokens are JWTs signed by the issuer with **RS256 only**. Asymmetric
   verification is mandatory: the gateway holds public keys, never a shared
   secret, so a token that verifies under a symmetric algorithm cannot have
   come from the issuer.
3. The gateway **must verify the signature** of every token before reading any
   claim for an authorization decision. Claim-level checks (issuer allowlist,
   audience, expiry, scope) are additional constraints layered on top of
   signature verification — they are not a substitute for it, because an
   attacker who can mint an unverified token can set those claims freely.
4. Verification keys are resolved from the issuer JWKS by `kid` and cached for
   at most `JWKS_TTL_SECONDS`. Revoked `kid` values are rejected before key
   resolution.
5. Required claims: `sub`, `iss`, `aud`, `exp`, `iat`, `scope`.
   - `aud` must equal `JWT_AUDIENCE`.
   - `iss` must be in `ALLOWED_ISSUERS`.
   - Clock skew tolerance is 5 seconds.
   - `exp - iat` must not exceed `MAX_TOKEN_LIFETIME_SECONDS` (3600).
6. Tokens with `token_use: refresh` are never accepted on resource routes.

## Issuance

1. Access tokens are signed with the RS256 private key referenced by
   `JWT_PRIVATE_KEY_PATH` and carry the active `kid` in the header.
2. If signing material cannot be resolved, issuance **must fail closed**. A
   deployment without key material is a misconfiguration, not a fallback mode;
   issuing a token under any other algorithm or placeholder key would produce
   credentials the issuer cannot vouch for.
3. Scopes must be members of `SCOPE_CATALOG`.

## Logging

Token strings, signatures, and any fragment of either are not permitted in log
output at any level. Log the `sub`, `tenant`, `kid`, and `jti` instead — `jti`
is the supported correlation handle for tracing an individual token.

## Trust boundaries

| Boundary                     | Untrusted input                             |
| ---------------------------- | ------------------------------------------- |
| Public internet → gateway    | `Authorization` header, request body        |
| Service mesh → `/v1/tokens`  | `X-Mesh-Client`, issuance payload           |
| Issuer JWKS → gateway        | JWKS document (schema-checked before use)   |
