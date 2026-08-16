# Endpoint contract

All endpoints require the `X-Api-Key` header. A missing or mismatched key
returns `401`. When the key is not configured in the environment, the service
returns `503` rather than serving the request: authorization checks fail
closed.

## GET /v1/tenants

Returns `{ "tenants": [...] }`.

## GET /v1/reports/summary

| Parameter | Required | Notes                     |
| --------- | -------- | ------------------------- |
| `tenant`  | yes      | Unknown tenant gives `404` |

Returns record counts and the captured total in minor units.

## Error shape

```json
{ "error": "invalid_request", "detail": "tenant is required" }
```

Client input problems are `400`. An unexpected server error is `500` and is
logged with a traceback; reaching `500` from ordinary client input is a defect.
