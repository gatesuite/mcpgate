---
title: How It Works
description: Key format, bcrypt storage, O(1) verification — the internals of MCPGate explained.
---

MCPGate is built around three ideas: keys that carry their own lookup ID, storage that never leaks, and a verify path fast enough to run on every request.

---

## Key format

Every key MCPGate generates follows this format:

```
mcp_sk_<public_id>_<secret>
│       │           │
│       │           64 hex chars (32 random bytes)
│       16 hex chars (8 random bytes) — stored in DB, used for lookup
configurable prefix (default: mcp_sk_)
```

**Example:**
```
mcp_sk_3f8a1c2e9b4d7f6a_4a7b2c9e1d3f8a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b
```

The public ID (`3f8a1c2e9b4d7f6a`) is indexed in the database. When a key arrives for verification, MCPGate extracts it directly from the key string — no full table scan needed.

:::tip[Why hex?]
`secrets.token_hex()` produces only `0-9a-f` — no underscores. This matters because `_` is the separator in the key format. Using base64url (`token_urlsafe`) would occasionally produce underscores in the random parts, breaking the parser.
:::

---

## Key generation

```python
public_id = secrets.token_hex(8)   # 16 hex chars — embedded in key, stored in DB
secret    = secrets.token_hex(32)  # 64 hex chars — never stored

plain_text_key = f"{prefix}{public_id}_{secret}"
# e.g. mcp_sk_3f8a1c2e9b4d7f6a_4a7b2c9e...
```

The plain-text key is returned **once** in the API response and never stored. What's stored:

| Field | Value | Purpose |
|-------|-------|---------|
| `public_id` | `3f8a1c2e9b4d7f6a` | Indexed — fast O(1) lookup |
| `key_hash` | `$2b$12$...` | bcrypt hash of the pre-hashed key |
| `prefix` | `mcp_sk_3f8a1c..._...5b` | Display string — safe to show users |

---

## Secure storage: SHA-256 + bcrypt

Bcrypt has a 72-byte input limit. A full MCPGate key is ~88 bytes — too long. The solution is a two-step hash:

```
plain_text_key
      │
      ▼
SHA-256(key)  →  64-char hex string  (always fits in bcrypt's 72-byte limit)
      │
      ▼
bcrypt(sha256_hex, salt)  →  stored key_hash
```

This means:
- bcrypt's 72-byte truncation bug can never trigger
- The stored hash is computationally infeasible to reverse
- Every key has a unique bcrypt salt (auto-generated per key)

On verification, the same two steps run on the incoming key and the result is compared against the stored hash using `bcrypt.checkpw`.

---

## Verification flow

```
Incoming request with key: mcp_sk_3f8a1c2e9b4d7f6a_4a7b2c...
                                    │
               ┌────────────────────┘
               │  1. Extract public_id from key string
               ▼
   SELECT * FROM api_keys WHERE public_id = '3f8a1c2e9b4d7f6a'
   AND is_active = TRUE
               │
               │  2. O(1) indexed lookup (public_id has a DB index)
               ▼
   bcrypt.checkpw(sha256(incoming_key), stored_key_hash)
               │
               │  3. Cryptographic verification
               ▼
   Check expires_at < now()
               │
               │  4. Expiry check
               ▼
   UPDATE api_keys SET last_used_at = now() WHERE id = ...
               │
               │  5. Audit trail update
               ▼
   {"valid": true, "user_id": "...", "scopes": {...}}
```

The verify endpoint **does not require admin authentication** — it's designed to be called on every MCP request at high frequency. The public ID extraction keeps it to a single indexed DB read.

---

## Scopes

Scopes are an arbitrary JSON object stored with each key:

```json
{"read": true, "write": false, "tools": ["search", "code"]}
```

MCPGate stores and returns them verbatim — your application enforces them. This gives you full flexibility without MCPGate needing to understand your permission model.

---

## Expiry

When creating a key with `expires_in_days`, MCPGate calculates an absolute UTC timestamp:

```
expires_at = now() + timedelta(days=N)
```

On every verify, if `expires_at` is set and in the past, the key is rejected with `"error": "Key expired"`. The key record is **not** automatically deleted — use the delete endpoint to clean up expired keys.

---

## Key prefix

The `KEY_PREFIX` env var (default: `mcp_sk_`) is prepended to every generated key. Change it to match your product:

```
KEY_PREFIX=myapp_sk_   →   myapp_sk_3f8a1c2e_...
KEY_PREFIX=agent_     →   agent_3f8a1c2e_...
```

The verify endpoint reads `KEY_PREFIX` at startup to validate incoming key format. Keys created with one prefix can't be verified with a different prefix setting.
