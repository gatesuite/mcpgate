---
title: Security
description: How MCPGate stores keys, why the design choices were made, and how to harden your deployment.
---

## Security model

MCPGate is built around the principle that **secrets should never be stored**. The plain-text API key is computed once, shown to the user once, and then discarded. Everything stored in the database is cryptographically derived and irreversible.

### Key design choices

| Choice | Reason |
|--------|--------|
| **SHA-256 pre-hash before bcrypt** | Bcrypt silently truncates inputs beyond 72 bytes — newer versions throw `ValueError`. Pre-hashing with SHA-256 normalizes any key to 64 bytes, safely within the limit, with no entropy loss. |
| **bcrypt for storage (not SHA-256 alone)** | bcrypt is slow by design — it adds a work factor that makes brute-force attacks expensive even if the database is compromised. SHA-256 alone is too fast for this purpose. |
| **Unique salt per key** | bcrypt generates a new random salt for every key. Two identical keys will have different hashes in the database. |
| **Public ID embedded in key** | Enables O(1) lookup without a full table scan. The public ID is not a secret — it's just an index pointer. The actual security comes from the bcrypt check. |
| **`token_hex` not `token_urlsafe`** | `token_urlsafe` uses base64url which includes `_` — the same character used as separator in the key format. Using hex avoids any parsing ambiguity. |
| **Hard delete on revoke** | Revoked keys are permanently removed. There is no "soft delete" state that could be accidentally re-enabled. |
| **Admin key checked via constant-time comparison** | FastAPI's `==` comparison on strings is not constant-time, but the admin key check is not on the hot path and the ADMIN_API_KEY is a pre-shared secret, not a user-facing secret. The verify path uses `bcrypt.checkpw` which is constant-time. |

---

## Key lifecycle

```
Generation:
  plain_key = prefix + token_hex(8) + "_" + token_hex(32)
  stored_hash = bcrypt( sha256(plain_key) )
  plain_key shown once → discarded

Storage (api_keys table):
  public_id   ← visible, indexed, not secret
  key_hash    ← bcrypt hash, irreversible
  prefix      ← display string, safe to show

Verification:
  bcrypt.checkpw( sha256(incoming_key), stored_hash )

Revocation:
  DELETE FROM api_keys WHERE id = ?
  (immediate, permanent)
```

---

## What's stored vs what's not

| Data | Stored | Notes |
|------|--------|-------|
| Plain-text key | ❌ Never | Shown once at creation, then gone |
| Key hash | ✅ | `bcrypt(sha256(plain_key))` — irreversible |
| Public ID | ✅ | Not secret — used as a lookup index |
| Display prefix | ✅ | Safe to show: `mcp_sk_<id>_...<last4>` |
| User ID | ✅ | Your application's user identifier |
| Scopes | ✅ | JSON blob — your app defines meaning |
| Expiry | ✅ | UTC timestamp, checked on verify |
| Last used | ✅ | Updated on every successful verify |

---

## Threat model

MCPGate assumes:

- **The database may be compromised.** The stored `key_hash` values cannot be reversed to recover plain-text keys due to bcrypt's one-way nature and random salts.
- **The `ADMIN_API_KEY` must stay secret.** If it leaks, an attacker can create/list/delete keys. Rotate it immediately if compromised.
- **The `/verify` endpoint is public.** It is designed to be called frequently. It reveals only `valid: true/false`, `user_id`, and `scopes` — no key material.
- **Network traffic should be encrypted.** MCPGate does not terminate TLS. Use an ingress controller or service mesh to enforce HTTPS.

MCPGate does **not** protect against:

- An attacker who can call the admin endpoints (protect with network policy / private load balancer)
- Key theft at the client side (the user's machine or MCP client)
- Replay attacks — verified keys remain valid until revoked or expired

---

## Hardening checklist

- [ ] `ADMIN_API_KEY` is at least 32 random bytes (`secrets.token_hex(32)`)
- [ ] `ADMIN_API_KEY` is stored in a secret manager (AWS Secrets Manager, GCP Secret Manager, Vault, Kubernetes Secret) — not in environment variables on the host
- [ ] MCPGate is not accessible from the public internet — only from your backend and MCP servers
- [ ] TLS is enforced at the ingress/load balancer level
- [ ] Set key expiry dates (`expires_in_days`) — avoid permanent keys unless genuinely needed
- [ ] Wire key revocation to user offboarding — when an account is deleted, delete its keys
- [ ] Monitor `last_used_at` — keys unused for 90+ days should be rotated or revoked
- [ ] Enable the PodDisruptionBudget in the Helm chart for HA deployments

---

## Rotating the admin key

The `ADMIN_API_KEY` is a pre-shared secret between MCPGate and your backend. To rotate it:

1. Generate a new key: `python3 -c "import secrets; print(secrets.token_hex(32))"`
2. Update your backend's env var / secret to the new value
3. Update MCPGate's env var / Kubernetes Secret
4. Restart MCPGate pods (rolling restart — no downtime with multiple replicas)

There is no grace period — the old key stops working immediately when MCPGate restarts.

---

## Reporting vulnerabilities

Please report security vulnerabilities privately via GitHub Security Advisories on the [MCPGate repository](https://github.com/gatesuite/mcpgate/security/advisories/new). Do not open a public issue for security concerns.
