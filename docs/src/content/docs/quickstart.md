---
title: Quick Start
description: Deploy MCPGate and issue your first API key in under 5 minutes.
---

## Prerequisites

- Docker and Docker Compose installed
- A PostgreSQL database (or use the bundled one)

---

## 1. Download and configure

```bash
curl -O https://raw.githubusercontent.com/gatesuite/mcpgate/main/docker-compose.yml
```

Generate a strong admin key:

```bash
export ADMIN_API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo "Save this somewhere safe: $ADMIN_API_KEY"
```

Create a `.env` file:

```bash
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://mcpgate:mcpgate@postgres:5432/mcpgate
ADMIN_API_KEY=$ADMIN_API_KEY
KEY_PREFIX=mcp_sk_
EOF
```

---

## 2. Start MCPGate

```bash
docker compose up -d
```

Check it's healthy:

```bash
curl http://localhost:8000/health
# {"status": "ok", "service": "mcpgate"}
```

---

## 3. Create your first API key

The `ADMIN_API_KEY` is your master credential — your backend uses it to manage keys on behalf of your users.

```bash
curl -X POST http://localhost:8000/api/v1/keys \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "name": "Claude Desktop",
    "scopes": {"read": true, "write": true}
  }'
```

Response:

```json
{
  "id": "a1b2c3d4-...",
  "key": "mcp_sk_3f8a1c2e9b4d7f6a_4a7b2c9e1d3f8a5b...",
  "prefix": "mcp_sk_3f8a1c2e9b4d7f6a_...5b",
  "user_id": "user_123",
  "name": "Claude Desktop",
  "created_at": "2026-04-16T10:00:00Z"
}
```

:::caution
The `key` field is only returned **once** at creation time. Store it securely and hand it to the user — MCPGate never shows it again.
:::

---

## 4. Verify a key

Your MCP server calls this on every incoming request:

```bash
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{"key": "mcp_sk_3f8a1c2e9b4d7f6a_4a7b2c9e1d3f8a5b..."}'
```

Response when valid:

```json
{
  "valid": true,
  "user_id": "user_123",
  "scopes": {"read": true, "write": true},
  "error": null
}
```

Response when invalid:

```json
{
  "valid": false,
  "user_id": null,
  "scopes": null,
  "error": "Invalid API key"
}
```

---

## 5. List and revoke keys

List all keys for a user:

```bash
curl http://localhost:8000/api/v1/keys/user_123 \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

Revoke a key by its ID:

```bash
curl -X DELETE http://localhost:8000/api/v1/keys/a1b2c3d4-... \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

---

## Pin a version

The root `docker-compose.yml` defaults to `latest`. For production, pin to a specific release:

```bash
MCPGATE_VERSION=1.2.3 docker compose up -d
```

Or set it in your `.env`:

```
MCPGATE_VERSION=1.2.3
```

---

## Next steps

- [How It Works](/mcpgate/how-it-works/) — key format, hashing, O(1) lookups
- [Integration Guide](/mcpgate/integration/) — wiring MCPGate into your app
- [API Reference](/mcpgate/api-reference/) — full endpoint documentation
- [Deployment](/mcpgate/deployment/) — Kubernetes with Helm
