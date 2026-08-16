# Audit note AUD-2024-11 (excerpt)

Source: internal platform security audit, gateway scope.

## Findings carried to the engineering backlog

| ID       | Area                | Note                                                                 | State    |
| -------- | ------------------- | -------------------------------------------------------------------- | -------- |
| AUD-11.1 | Token claim checks  | Gateway relied on library defaults; issuer and lifetime not enforced  | assigned |
| AUD-11.2 | Key revocation      | No revocation path for a compromised `kid`                            | assigned |
| AUD-11.3 | Log hygiene         | Refund log lines include actor identifiers; acceptable, retention 30d | closed   |
| AUD-11.4 | JWKS availability   | Cache TTL 300s; issuer outage tolerated for one TTL window            | accepted |
| AUD-11.5 | Mesh authentication | `/v1/tokens` gated by header only; mesh mTLS assumed at ingress       | accepted |

AUD-11.1 and AUD-11.2 were assigned to the gateway team and are the stated
motivation for the change in `patches/`.

## Out of scope for this audit

- Ledger service internals
- Client SDK token caching behavior
- Terraform for the mesh ingress
