---
title: Integration Guide
description: Wire MCPGate into your application — issue keys to users, verify on every MCP request, revoke when needed.
---

MCPGate sits between your application and your MCP server. Your backend manages keys via the admin API; your MCP server verifies them on every request.

```
User         Your App (backend)       MCPGate          MCP Server
 │                   │                    │                  │
 │── signup ────────▶│                    │                  │
 │                   │── POST /keys ─────▶│                  │
 │                   │◀─ {key: mcp_sk_...}│                  │
 │◀── key ───────────│                    │                  │
 │                   │                    │                  │
 │── MCP request ────────────────────────────────────────────▶│
 │                   │                    │◀─ POST /verify ──│
 │                   │                    │── {valid: true} ─▶│
 │◀── response ───────────────────────────────────────────────│
```

---

## Step 1 — Issue a key when a user connects

When a user connects an MCP client (Claude Desktop, Cursor, etc.), your backend creates a key for them and returns it once:

```python
import httpx

async def create_mcp_key(user_id: str, name: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://mcpgate:8000/api/v1/keys",
            headers={"Authorization": f"Bearer {ADMIN_API_KEY}"},
            json={
                "user_id": user_id,
                "name": name,
                "scopes": {"read": True, "write": True},
                "expires_in_days": 365,
            },
        )
        resp.raise_for_status()
        return resp.json()["key"]   # mcp_sk_... — return to user, never store
```

```typescript
async function createMcpKey(userId: string, name: string): Promise<string> {
  const resp = await fetch("http://mcpgate:8000/api/v1/keys", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.ADMIN_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ user_id: userId, name, scopes: { read: true } }),
  });
  const data = await resp.json();
  return data.key; // mcp_sk_... — return to user, never store
}
```

:::caution[Show the key once]
The `key` field in the response is the only time MCPGate reveals the plain-text key. Display it to the user immediately and do not store it in your database — if they lose it, issue a new one.
:::

---

## Step 2 — Verify on every MCP request

Your MCP server calls `/verify` before processing any request. The endpoint is unauthenticated and optimized for high-frequency calls:

```python
import httpx

async def verify_mcp_key(key: str) -> dict | None:
    """Returns user info if valid, None if invalid."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://mcpgate:8000/api/v1/verify",
            json={"key": key},
        )
        data = resp.json()
        if not data["valid"]:
            return None
        return {"user_id": data["user_id"], "scopes": data["scopes"]}
```

```typescript
async function verifyMcpKey(key: string) {
  const resp = await fetch("http://mcpgate:8000/api/v1/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key }),
  });
  const data = await resp.json();
  return data.valid ? { userId: data.user_id, scopes: data.scopes } : null;
}
```

```go
type VerifyResponse struct {
    Valid   bool            `json:"valid"`
    UserID  string          `json:"user_id"`
    Scopes  map[string]any  `json:"scopes"`
    Error   string          `json:"error"`
}

func verifyMcpKey(key string) (*VerifyResponse, error) {
    body, _ := json.Marshal(map[string]string{"key": key})
    resp, err := http.Post("http://mcpgate:8000/api/v1/verify",
        "application/json", bytes.NewReader(body))
    if err != nil {
        return nil, err
    }
    var result VerifyResponse
    json.NewDecoder(resp.Body).Decode(&result)
    if !result.Valid {
        return nil, nil
    }
    return &result, nil
}
```

### Enforcing scopes

MCPGate returns scopes verbatim — your server decides what they mean:

```python
async def handle_mcp_request(key: str, tool: str):
    auth = await verify_mcp_key(key)
    if auth is None:
        raise Unauthorized("Invalid API key")

    scopes = auth.get("scopes") or {}

    if tool in ("write_file", "execute_code") and not scopes.get("write"):
        raise Forbidden("Key does not have write scope")

    # proceed...
```

---

## Step 3 — List keys for a user

Show users which keys they have active (prefix only — never the secret):

```python
async def list_user_keys(user_id: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"http://mcpgate:8000/api/v1/keys/{user_id}",
            headers={"Authorization": f"Bearer {ADMIN_API_KEY}"},
        )
        return resp.json()
        # [{"id": "...", "prefix": "mcp_sk_3f8a1c..._...5b",
        #   "name": "Claude Desktop", "scopes": {...},
        #   "created_at": "...", "last_used_at": "..."}]
```

The `prefix` field (e.g. `mcp_sk_3f8a1c..._...5b`) is safe to display — it identifies the key without exposing the secret.

---

## Step 4 — Revoke a key

When a user disconnects a client or you detect a compromised key:

```python
async def revoke_key(key_id: str) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"http://mcpgate:8000/api/v1/keys/{key_id}",
            headers={"Authorization": f"Bearer {ADMIN_API_KEY}"},
        )
        resp.raise_for_status()  # 204 No Content on success
```

After revocation, any verify call with that key returns `{"valid": false, "error": "Invalid API key"}` immediately.

---

## Where MCPGate fits alongside OAuth

MCPGate handles **machine authorization** — it does not replace your existing user auth. A common setup:

```
Auth0 / Clerk / Firebase     ←── Human login (OAuth, SSO)
MCPGate                      ←── Machine auth (API keys for MCP clients)
```

Your users log in via OAuth. Once logged in, your app calls MCPGate to issue them an API key for their MCP client. MCPGate never sees passwords or OAuth tokens.

---

## Production checklist

- [ ] `ADMIN_API_KEY` is a strong random secret (at least 32 bytes), stored in a secret manager
- [ ] MCPGate is not exposed to the public internet — accessible only from your backend and MCP server
- [ ] Keys have expiry dates set (`expires_in_days`) unless you need permanent keys
- [ ] Scopes are validated in your MCP server, not just returned
- [ ] Key revocation is wired to your user offboarding flow
- [ ] `last_used_at` is surfaced to users so they can identify unused keys
