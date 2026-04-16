# MCPGate

An ultra-fast, open-source API Key lifecycle and verification microservice. Built specifically to secure Model Context Protocol (MCP) servers and AI Agents.

<p align="center">
  <img src="./excalidraw/architecture.svg" alt="MCPGate Architecture" />
</p>

## Why MCPGate?

As AI agents (like Claude Desktop, Cursor, etc.) increasingly connect to remote SaaS applications via the Model Context Protocol, developers need a way to issue secure, scoped API keys to their users.

**MCPGate** sits alongside your existing authentication provider (Auth0, Clerk, Firebase, or AuthGate). While your existing provider handles *Human OAuth*, MCPGate handles *Machine Authorization*.

### Features
- **Blazing Fast Verification**: Sub-millisecond key validation using O(1) database lookups.
- **Secure by Default**: Stores only hashed representations of keys (bcrypt). The plain-text key is never saved.
- **Identifiable Prefixes**: Generates Stripe-style keys (e.g., `mcp_sk_abc123_xyz987`) so users can easily identify them.
- **Scoped Access**: Attach JSON scopes to any key (e.g., `{"read": true, "write": false}`).

## Quick Start

1. Start the service:
```bash
docker compose up -d
```

2. Test the health endpoint:
```bash
curl http://localhost:8001/health
```

## API Reference

All administrative endpoints require the `Authorization: Bearer <ADMIN_API_KEY>` header.
This key is configured via the `ADMIN_API_KEY` environment variable.

### 1. Create a Key
*Your backend calls this when a user clicks "Generate API Key" in your dashboard.*

```bash
curl -X POST http://localhost:8001/api/v1/keys \
  -H "Authorization: Bearer super-secret-admin-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "usr_12345",
    "name": "Claude Desktop",
    "scopes": {"read": true, "delete": false}
  }'
```
**Response:**
```json
{
  "id": "uuid...",
  "name": "Claude Desktop",
  "prefix": "mcp_sk_abc123_...4f5e",
  "key": "mcp_sk_abc123_longsecrethere",  // Only shown once!
  "user_id": "usr_12345",
  "created_at": "2026-03-25T..."
}
```

### 2. Verify a Key
*Your backend calls this on every incoming request from an MCP Server to validate the agent's key.*

```bash
curl -X POST http://localhost:8001/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "key": "mcp_sk_abc123_longsecrethere"
  }'
```
**Response:**
```json
{
  "valid": true,
  "user_id": "usr_12345",
  "scopes": {"read": true, "delete": false},
  "error": null
}
```

### 3. List a User's Keys
```bash
curl http://localhost:8001/api/v1/keys/usr_12345 \
  -H "Authorization: Bearer super-secret-admin-key-change-me"
```

### 4. Revoke a Key
```bash
curl -X DELETE http://localhost:8001/api/v1/keys/{key_id} \
  -H "Authorization: Bearer super-secret-admin-key-change-me"
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `ADMIN_API_KEY` | Master token for creating/revoking keys | |
| `KEY_PREFIX` | Prefix for generated keys | `mcp_sk_` |
