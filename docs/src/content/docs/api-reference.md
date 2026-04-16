---
title: API Reference
description: Complete reference for all MCPGate endpoints — request schemas, response schemas, and error codes.
---

## Base URL

```
http://your-mcpgate-host:8000/api/v1
```

Health check (no auth):

```
http://your-mcpgate-host:8000/health
```

---

## Authentication

All admin endpoints require an `Authorization` header:

```
Authorization: Bearer <ADMIN_API_KEY>
```

The `/verify` endpoint is **intentionally unauthenticated** — it is the high-frequency path called by MCP servers on every request.

---

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/keys` | Admin | Create a new API key |
| `GET` | `/api/v1/keys/{user_id}` | Admin | List all keys for a user |
| `DELETE` | `/api/v1/keys/{key_id}` | Admin | Revoke and delete a key |
| `POST` | `/api/v1/verify` | None | Verify an incoming key |
| `GET` | `/health` | None | Health check |

---

## POST /api/v1/keys

Create a new API key for a user. Returns the plain-text key **once only**.

### Request

```json
{
  "user_id": "user_123",
  "name": "Claude Desktop",
  "scopes": {"read": true, "write": false},
  "expires_in_days": 365
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | string | ✅ | ID of the user in your application |
| `name` | string | — | Human-readable label (e.g. "Claude Desktop") |
| `scopes` | object | — | Arbitrary JSON permissions object |
| `expires_in_days` | integer | — | Days until expiry. Omit for no expiry. Use `-1` to create an already-expired key (testing). |

### Response `200 OK`

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "key": "mcp_sk_3f8a1c2e9b4d7f6a_4a7b2c9e1d3f8a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b",
  "prefix": "mcp_sk_3f8a1c2e9b4d7f6a_...9b",
  "user_id": "user_123",
  "name": "Claude Desktop",
  "created_at": "2026-04-16T10:00:00Z"
}
```

| Field | Description |
|-------|-------------|
| `id` | UUID — use this to revoke the key |
| `key` | Full plain-text key — **shown once, never retrievable again** |
| `prefix` | Safe display string — show to users to identify the key |
| `user_id` | Echoed from request |
| `name` | Echoed from request |
| `created_at` | UTC timestamp |

### Errors

| Status | Description |
|--------|-------------|
| `401` | Missing or malformed `Authorization` header |
| `403` | Wrong `ADMIN_API_KEY` |
| `422` | Missing required field (`user_id`) |

---

## GET /api/v1/keys/{user_id}

List all keys belonging to a user. Never includes the plain-text key — only safe display fields.

### Response `200 OK`

```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "prefix": "mcp_sk_3f8a1c2e9b4d7f6a_...9b",
    "name": "Claude Desktop",
    "user_id": "user_123",
    "scopes": {"read": true, "write": false},
    "is_active": true,
    "created_at": "2026-04-16T10:00:00Z",
    "last_used_at": "2026-04-16T14:32:11Z",
    "expires_at": "2027-04-16T10:00:00Z"
  }
]
```

Returns an empty array `[]` if the user has no keys. Results are ordered newest first.

| Field | Description |
|-------|-------------|
| `id` | UUID — use this to revoke |
| `prefix` | Safe display string |
| `is_active` | Always `true` for listed keys (inactive keys are deleted) |
| `last_used_at` | UTC timestamp of last successful verify, or `null` if never used |
| `expires_at` | UTC expiry timestamp, or `null` if no expiry |

### Errors

| Status | Description |
|--------|-------------|
| `401` | Missing or malformed `Authorization` header |
| `403` | Wrong `ADMIN_API_KEY` |

---

## DELETE /api/v1/keys/{key_id}

Permanently delete a key. Immediately stops future verifications. This is a hard delete — the key record is removed from the database.

### Response `204 No Content`

No body. A `204` is returned whether the key existed or not.

### Errors

| Status | Description |
|--------|-------------|
| `401` | Missing or malformed `Authorization` header |
| `403` | Wrong `ADMIN_API_KEY` |

---

## POST /api/v1/verify

Verify an incoming API key. This endpoint is **not authenticated** and optimized for high-frequency use — call it on every MCP request.

Always returns `200 OK`. Check the `valid` field, not the HTTP status code.

### Request

```json
{
  "key": "mcp_sk_3f8a1c2e9b4d7f6a_4a7b2c9e..."
}
```

### Response `200 OK` — valid key

```json
{
  "valid": true,
  "user_id": "user_123",
  "scopes": {"read": true, "write": false},
  "error": null
}
```

### Response `200 OK` — invalid key

```json
{
  "valid": false,
  "user_id": null,
  "scopes": null,
  "error": "Invalid API key"
}
```

### Error values

| `error` | Cause |
|---------|-------|
| `"Invalid key format"` | Key doesn't start with `KEY_PREFIX`, or has wrong structure |
| `"Invalid API key"` | Key not found in DB, or bcrypt check failed |
| `"Key expired"` | Key exists but `expires_at` is in the past |

:::tip[Always check `valid`, not `error`]
The absence of an `error` field does not mean the key is valid. Always gate on `data.valid === true`.
:::

---

## GET /health

Liveness check. Used by Kubernetes probes and load balancers.

### Response `200 OK`

```json
{
  "status": "ok",
  "service": "mcpgate"
}
```

No authentication required.
