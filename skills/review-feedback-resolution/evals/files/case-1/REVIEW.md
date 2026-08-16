# Code Review — auth-service (feature/oidc-login)

Review target:
- Revision: `abc1234`
- Branch: `feature/oidc-login`
- Diff range: `main...feature/oidc-login`
- Applicable tests: `pytest tests/auth_service_test.py`
- Contracts: `OidcToken` dataclass fields, `validate_token` expiry semantics,
  `bootstrap_session` rejection of invalid tokens.

Nine inline comments follow. Each is a discrete review note; disposition it
independently against the source (`auth_service.py`) and the frozen context.

---

## Comment 1 (line ~28, `SESSION_LIFETIME_SECONDS`)
> "3600 seconds is too short for an SSO session. Bump it to 24 hours."

The constant is a documented contract; there is no test asserting the value and
no stated requirement for 24h sessions. This is a product-policy preference, not
a code defect.

## Comment 2 (line ~37, `fetch_well_known`)
> "You should cache the discovery document, calling it every time is wasteful."

`exchange_code_for_token` is invoked once per login, not in a hot path. The
suggestion is a performance optimization with no evidence of a real bottleneck.

## Comment 3 (line ~52, `validate_token`)
> "`validate_token` only checks expiry, it never verifies the signature."

`OidcToken` is an internal, already-validated representation produced after the
real token endpoint exchange. Signature verification happens upstream at the
token endpoint (`exchange_code_for_token`), which is out of this module's scope.

## Comment 4 (line ~60, `exchange_code_for_token`)
> "`subject = code[:8]` truncates the subject to 8 chars — collisions are
> possible across users."

The subject is derived from an opaque authorization code, not the user identity.
Persistent subject mapping is owned by the identity provider; truncating the
code here is only a correlation hint. Needs a precise anchor to be actionable.

## Comment 5 (line ~60, `exchange_code_for_token`)
> "Add a `# TODO` here to revisit the subject mapping."

A vague placeholder with no concrete defect or evidence. What specifically is
wrong, and what is the correct behavior?

## Comment 6 (line ~70, `bootstrap_session`)
> "`bootstrap_session` raises `ValueError` for invalid tokens — shouldn't it
> return None instead?"

`validate_token` is re-checked defensively here, matching the documented
contract that invalid tokens must be rejected. Raising is consistent with the
module's error model; changing it would alter the public contract.

## Comment 7 (line ~71, `bootstrap_session` return dict)
> "The `granted_at` timestamp duplicates `expires_at` minus the lifetime."

`granted_at` records when the session was actually issued, which can differ from
`expires_at - SESSION_LIFETIME_SECONDS` if clocks or lifetimes change. It is not
strictly redundant.

## Comment 8 (line ~60, `exchange_code_for_token` vs Comment 4)
> "Same point as comment 4 — the subject handling needs a real fix."

This repeats Comment 4's concern about subject mapping. Resolve once and link
the pair rather than tracking twice.

## Comment 9 (line ~37, `fetch_well_known` docstring)
> "The docstring says the caller handles TLS but there is no caller shown here."

True — `fetch_well_known` is called from `exchange_code_for_token`, which is the
caller responsible for the outbound request's TLS. The docstring is accurate.
