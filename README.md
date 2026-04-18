# MCPGate

**Ultra-fast API key lifecycle and verification service for MCP servers and AI agents.**

> Plug-and-play machine authorization — deploy as a sidecar, secure your AI infrastructure in minutes.

<p align="center">
  <img src="./excalidraw/architecture.svg" alt="MCPGate Architecture" />
</p>

---

## Why MCPGate?

As AI agents (Claude Desktop, Cursor, custom MCP clients) increasingly connect to remote SaaS applications via the Model Context Protocol, developers need a way to issue secure, scoped API keys to their users.

**MCPGate sits alongside your existing human auth provider** (Auth0, Clerk, Firebase, AuthGate). While those handle *human OAuth*, MCPGate handles *machine authorization* — issuing, verifying, and revoking API keys for programmatic clients.

We looked at what's already out there:

| Solution | Problem |
|----------|---------|
| **Roll your own** | Easy to get wrong — bcrypt 72-byte truncation, key parsing bugs, plain-text leaks |
| **API Gateway (Kong, Tyk)** | Heavy, expensive, complex config for a simple use case |
| **OAuth tokens** | Designed for human login flows, not machine clients |
| **Static secrets** | No rotation, no scopes, no revocation, no audit trail |

**MCPGate fills the gap** — a purpose-built API key service with Stripe-style keys, bcrypt storage, O(1) verification, and a ~50MB container.

### MCPGate vs rolling your own

| | **MCPGate** | **DIY** |
|---|---|---|
| **Key format** | `mcp_sk_<id>_<secret>` — scannable, unambiguous | Whatever you build |
| **Storage** | SHA-256 pre-hash + bcrypt — correct by default | Easy to get wrong |
| **Lookup speed** | O(1) — public ID indexed in DB | Often O(n) — full table scan |
| **Scopes** | JSON blob on every key | Extra schema work |
| **Expiry** | Built-in, checked on every verify | Often forgotten |
| **Revocation** | Hard delete via API | Varies |
| **Audit trail** | `last_used_at` updated on every verify | Extra work |
| **Deployment** | Single container, Helm chart included | You build it |

**When to use MCPGate:** You're building an MCP server or AI tool that accepts programmatic requests and need a complete key management solution — issuance, verification, scopes, expiry, audit — without writing any of it yourself.

**When not to:** You need OAuth flows, SSO, MFA, or human login UI. Use AuthGate, Auth0, Clerk, or similar for that — and run MCPGate alongside it for machine keys.

---

## Features

- **Blazing-fast verification** — sub-millisecond key validation via O(1) indexed lookups
- **Secure by default** — SHA-256 pre-hash + bcrypt; plain-text keys never stored
- **Stripe-style keys** — identifiable format (`mcp_sk_abc123_xyz987`) users can recognize at a glance
- **Scoped access** — attach arbitrary JSON scopes to any key (`{"read": true, "write": false}`)
- **Expiry support** — optional `expires_in_days` on key creation, enforced on every verify
- **Audit trail** — `last_used_at` timestamp updated on every successful verify
- **Kubernetes-ready** — Helm chart with HPA, PDB, read-only filesystem, non-root user
- **Docker-first** — multi-stage build, ~50MB image, docker-compose for local dev
- **Async & fast** — built on FastAPI + asyncpg with full async I/O
- **Fully tested** — E2E test suite gates every release via GitHub Actions

---

## Quick Start

### One-command deploy (recommended)

```bash
curl -O https://raw.githubusercontent.com/gatesuite/mcpgate/main/docker-compose.yml
export ADMIN_API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
docker compose up -d
```

Check it's up:

```bash
curl http://localhost:8000/health
# {"status": "ok", "service": "mcpgate"}
```

**That's it.** No config files to create, no repo to clone. Postgres is bundled in the same stack. The published `ghcr.io/gatesuite/mcpgate:latest` image is used.

To pin a specific version instead of `latest`:

```bash
export MCPGATE_VERSION=1.2.3
docker compose up -d
```

### For contributors: build from source

```bash
git clone https://github.com/gatesuite/mcpgate.git
cd mcpgate

# 1. Create your env file
cp .env.example .env
# Edit .env — set a strong ADMIN_API_KEY

# 2. Start the stack (builds from local Dockerfile)
make app-up
```

The compose file in `deployments/docker-compose/` reads credentials from `.env` and builds the production Dockerfile target.

### Without Docker

```bash
# Prerequisites: Python 3.12+, PostgreSQL
pip install -r requirements.txt

export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mcpgate
export ADMIN_API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | Async PostgreSQL URI (`postgresql+asyncpg://...`) |
| `ADMIN_API_KEY` | ✅ | — | Master token for admin endpoints (create/list/revoke) |
| `KEY_PREFIX` | — | `mcp_sk_` | Prefix prepended to all generated keys |
| `PROJECT_NAME` | — | `MCPGate` | Service name in API responses |
| `VERSION` | — | `1.0.0` | Version string |
| `API_V1_STR` | — | `/api/v1` | API route prefix |

Generate a strong admin key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Keep `ADMIN_API_KEY` in a secret manager in production (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault, or a Kubernetes Secret). Never commit it.

---

## Integration Guide

### How it works

```
User        Your App (backend)       MCPGate         MCP Server
 │                  │                    │                 │
 │── signup ───────▶│                    │                 │
 │                  │── POST /keys ─────▶│                 │
 │                  │◀─ {key: mcp_sk_…} ─│                 │
 │◀── key ──────────│                    │                 │
 │                  │                    │                 │
 │── MCP request ───────────────────────────────────────── ▶│
 │                  │                    │◀─ POST /verify ─│
 │                  │                    │── {valid:true} ▶│
 │◀── response ─────────────────────────────────────────────│
```

### Step 1 — Issue a key

When a user connects an MCP client, your backend creates a key for them. The `ADMIN_API_KEY` authorizes this call — never expose it to the browser or end users.

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
        return resp.json()["key"]   # mcp_sk_... — return to user, never store
```

> **The `key` field is only returned once** at creation time. Display it to the user immediately and do not store it — if they lose it, issue a new one.

### Step 2 — Verify on every MCP request

Your MCP server calls `/verify` before processing any request. The endpoint is unauthenticated and optimized for high-frequency calls:

```python
async def verify_mcp_key(key: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://mcpgate:8000/api/v1/verify",
            json={"key": key},
        )
        data = resp.json()
        return data if data["valid"] else None
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

### Step 3 — Enforce scopes in your server

MCPGate returns scopes verbatim — your MCP server decides what they mean:

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

### Step 4 — Revoke when needed

When a user disconnects a client or you detect a compromised key:

```bash
curl -X DELETE http://mcpgate:8000/api/v1/keys/{key_id} \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

After revocation, any verify call with that key returns `{"valid": false, "error": "Invalid API key"}` immediately.

---

## API Reference

All administrative endpoints require the `Authorization: Bearer <ADMIN_API_KEY>` header. The `/verify` endpoint is **intentionally unauthenticated** — it is the high-frequency path called by MCP servers on every request.

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/keys` | POST | Admin | Create a new API key |
| `/api/v1/keys/{user_id}` | GET | Admin | List all keys for a user |
| `/api/v1/keys/{key_id}` | DELETE | Admin | Revoke and delete a key |
| `/api/v1/verify` | POST | None | Verify an incoming key |
| `/health` | GET | None | Health check |

### Create a Key

```bash
curl -X POST http://localhost:8000/api/v1/keys \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "usr_12345",
    "name": "Claude Desktop",
    "scopes": {"read": true, "write": false},
    "expires_in_days": 365
  }'
```

**Response:**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "key": "mcp_sk_3f8a1c2e9b4d7f6a_4a7b2c9e...",
  "prefix": "mcp_sk_3f8a1c2e9b4d7f6a_...9b",
  "user_id": "usr_12345",
  "name": "Claude Desktop",
  "created_at": "2026-04-16T10:00:00Z"
}
```

### Verify a Key

```bash
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{"key": "mcp_sk_3f8a1c2e9b4d7f6a_4a7b2c9e..."}'
```

**Success response:**

```json
{
  "valid": true,
  "user_id": "usr_12345",
  "scopes": {"read": true, "write": false},
  "error": null
}
```

**Failure response:**

```json
{ "valid": false, "user_id": null, "scopes": null, "error": "Invalid API key" }
```

> **Note:** `/verify` always returns HTTP `200 OK` — check the `valid` boolean, not the status code. The `error` field holds the reason (`"Invalid key format"`, `"Invalid API key"`, or `"Key expired"`).

### List a User's Keys

```bash
curl http://localhost:8000/api/v1/keys/usr_12345 \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

Returns an array of keys (never including the plain-text secret), ordered newest first.

### Revoke a Key

```bash
curl -X DELETE http://localhost:8000/api/v1/keys/{key_id} \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

Returns `204 No Content`. This is a hard delete — the key record is permanently removed from the database.

---

## Managing Keys

### Finding expired keys

MCPGate does not automatically delete expired keys — verification rejects them, but the rows stay in the database. Clean them up periodically:

```sql
-- List expired keys
SELECT id, user_id, prefix, expires_at
FROM api_keys
WHERE expires_at < NOW();

-- Bulk delete expired keys older than 30 days
DELETE FROM api_keys
WHERE expires_at < NOW() - INTERVAL '30 days';
```

### Finding unused keys

Keys that have never been used — or haven't been used in a long time — are candidates for rotation or revocation:

```sql
-- Keys never used
SELECT id, user_id, prefix, created_at
FROM api_keys
WHERE last_used_at IS NULL
  AND created_at < NOW() - INTERVAL '30 days';

-- Keys unused in the last 90 days
SELECT id, user_id, prefix, last_used_at
FROM api_keys
WHERE last_used_at < NOW() - INTERVAL '90 days';
```

Surface `last_used_at` in your user-facing key management UI so users can identify stale keys themselves.

### Rotating a key

There is no in-place rotation — issue a new key, hand it to the user, then delete the old one:

```python
# 1. Create a replacement
new_key = await create_mcp_key(user_id="usr_12345", name="Claude Desktop (rotated)")

# 2. Deliver new_key to the user

# 3. Delete the old key (fetch its ID via GET /keys/{user_id} first)
await client.delete(f"http://mcpgate:8000/api/v1/keys/{old_key_id}",
                    headers={"Authorization": f"Bearer {ADMIN_API_KEY}"})
```

### Auditing key usage

The `last_used_at` column is your simplest audit tool. For richer analytics, run MCPGate's access logs through your log pipeline — every `POST /api/v1/verify` call is logged.

---

## Deployment

### Docker Compose (local dev)

```bash
make app-up     # builds production image, starts MCPGate + Postgres
make app-logs   # tail logs
make app-down   # stop (volumes preserved)
```

### Kubernetes (Helm via OCI)

**Step 1: Create the Secret**

```bash
kubectl create secret generic mcpgate-secrets \
  --from-literal=DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/mcpgate" \
  --from-literal=ADMIN_API_KEY="$(openssl rand -hex 32)"
```

**Step 2: Install the chart**

```bash
helm install mcpgate oci://ghcr.io/gatesuite/charts/mcpgate \
  --set existingSecret=mcpgate-secrets
```

Or use a `values.yaml` override:

```bash
helm install mcpgate oci://ghcr.io/gatesuite/charts/mcpgate -f my-values.yaml
```

To install from source instead:

```bash
helm install mcpgate ./deployments/helm/mcpgate -f my-values.yaml
```

**Production defaults included:** HPA (1-10 replicas, CPU/memory scaling), topology spread, read-only root filesystem, non-root user, startup/liveness/readiness probes, zero-downtime rolling updates.

### Kubernetes (raw manifests)

If you prefer raw manifests over Helm, here's a minimal production setup:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mcpgate-secrets
type: Opaque
stringData:
  DATABASE_URL: postgresql+asyncpg://user:pass@postgres:5432/mcpgate
  ADMIN_API_KEY: your-strong-secret-here
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcpgate
spec:
  replicas: 2
  selector:
    matchLabels: { app: mcpgate }
  template:
    metadata:
      labels: { app: mcpgate }
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: mcpgate
          image: ghcr.io/gatesuite/mcpgate:latest
          ports:
            - containerPort: 8000
          envFrom:
            - secretRef:
                name: mcpgate-secrets
          livenessProbe:
            httpGet: { path: /health, port: 8000 }
          readinessProbe:
            httpGet: { path: /health, port: 8000 }
          resources:
            requests: { cpu: 50m, memory: 64Mi }
            limits:   { cpu: 250m, memory: 128Mi }
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
---
apiVersion: v1
kind: Service
metadata:
  name: mcpgate
spec:
  selector: { app: mcpgate }
  ports:
    - port: 8000
      targetPort: 8000
```

Expose via your ingress controller (NGINX, Traefik, cloud load balancer) as needed. MCPGate should never be exposed to the public internet — keep it on a private service mesh accessible only by your backend and MCP servers.

### Make Targets

| Command | Description |
|---------|-------------|
| `make app-up` | Build and start MCPGate + Postgres from source |
| `make app-down` | Stop MCPGate (volumes preserved) |
| `make app-logs` | Tail MCPGate container logs |
| `make docs-up` | Start docs dev server (port 4321) |
| `make docs-down` | Stop docs container |
| `make test-run` | Run E2E tests (pytest + real Postgres) |
| `make test-down` | Stop test containers |
| `make clean` | Wipe containers, volumes, caches |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (async Python) |
| Database | PostgreSQL + asyncpg + SQLAlchemy |
| Hashing | bcrypt + SHA-256 pre-hash |
| Validation | Pydantic v2 |
| Container | Docker (multi-stage, ~50MB) |
| Orchestration | Helm / Docker Compose |
| CI/CD | GitHub Actions + release-please |
| Testing | pytest + pytest-asyncio + httpx |

---

## Architecture

### Kubernetes Deployment

```mermaid
graph TB
    Backend["🖥️ Your Backend"]
    MCPServer["🤖 Your MCP Server"]

    subgraph EKS Cluster
        subgraph Private["Private (ClusterIP Services)"]
            MG["MCPGate<br/>ClusterIP :8000"]
            PG["PostgreSQL<br/>ClusterIP :5432"]
        end
    end

    Backend -->|"Admin API<br/>(create/list/revoke)"| MG
    MCPServer -->|"Verify on every request<br/>POST /verify"| MG
    MG -->|"Async"| PG

    style MG fill:#10b981,stroke:#047857,color:#fff
    style PG fill:#6366f1,stroke:#4338ca,color:#fff
    style Backend fill:#3b82f6,stroke:#1d4ed8,color:#fff
    style MCPServer fill:#f59e0b,stroke:#d97706,color:#fff
```

### Key Verification Flow

```mermaid
sequenceDiagram
    actor User
    participant Client as MCP Client (Claude Desktop, etc.)
    participant MCP as Your MCP Server
    participant MG as MCPGate
    participant DB as PostgreSQL

    User->>Client: Use MCP tool
    Client->>MCP: Request with API key header
    MCP->>MG: POST /api/v1/verify { key: "mcp_sk_..." }
    MG->>MG: Extract public_id from key
    MG->>DB: SELECT WHERE public_id = ? AND is_active = true
    DB-->>MG: Return key record
    MG->>MG: bcrypt.checkpw(sha256(key), stored_hash)
    MG->>MG: Check expires_at
    MG->>DB: UPDATE last_used_at = now()
    MG-->>MCP: { valid: true, user_id, scopes }
    MCP->>MCP: Check scopes, enforce permissions
    MCP-->>Client: Tool result
    Client-->>User: Display result
```

---

## Project Structure

```
mcpgate/
├── app/
│   ├── main.py              # FastAPI entrypoint, lifespan, CORS
│   ├── api/
│   │   └── routes.py        # All 5 endpoints: create, list, delete, verify, health
│   ├── core/
│   │   ├── config.py        # Settings via pydantic-settings + .env
│   │   ├── database.py      # Async SQLAlchemy engine + session factory
│   │   └── security.py      # Key generation, SHA-256 pre-hash, bcrypt hash/verify
│   ├── models/
│   │   └── api_key.py       # ApiKey SQLAlchemy ORM model
│   └── schemas/
│       └── api_key.py       # Pydantic request/response schemas
├── tests/
│   ├── conftest.py          # Fixtures: client, admin_headers, DB setup/teardown
│   ├── test_health.py       # Health endpoint
│   ├── test_keys.py         # Create, list, revoke (with/without auth)
│   └── test_verify.py       # Valid, invalid, expired, revoked, tampered keys
├── deployments/
│   ├── docker-compose/      # Dev compose (builds from local Dockerfile)
│   └── helm/mcpgate/        # Kubernetes Helm chart
├── docs/                    # Astro/Starlight documentation site
├── .github/workflows/       # CI/CD: release-please, e2e, docker-publish, docs
├── Dockerfile               # Multi-stage: production + test targets
├── docker-compose.yml       # End-user zero-config deploy (pulls from GHCR)
├── docker-compose.test.yml  # Test runner (make test-run)
└── Makefile                 # app-*, docs-*, test-* targets
```

---

## Security

- **SHA-256 + bcrypt storage** — plain-text keys never stored; irreversible one-way hash
- **Unique salt per key** — identical keys produce different hashes in the database
- **Constant-time verification** — `bcrypt.checkpw` on the hot path prevents timing attacks
- **Hard delete on revoke** — no soft-delete state that could be accidentally re-enabled
- **Non-root container** — runs as unprivileged user in Docker and Kubernetes
- **Read-only root filesystem** — container can't modify its own image at runtime
- **Admin key separation** — master token never touches the verification hot path; `/verify` is unauthenticated by design
- **Threat model & hardening** — see the [Security docs](https://gatesuite.github.io/mcpgate/security/) for the full threat model and production checklist

Report vulnerabilities privately via [GitHub Security Advisories](https://github.com/gatesuite/mcpgate/security/advisories/new).

---

## Release Process

MCPGate uses [release-please](https://github.com/googleapis/release-please) for automated versioning:

1. Commits to `main` follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, etc.)
2. Release-please opens a PR with version bump + changelog entry
3. When the PR is merged, a new tag and GitHub Release are created automatically
4. Tag creation triggers the Docker image and Helm chart to be published to GHCR
5. The full E2E test suite runs before any release artifact is published — no broken version reaches users

---

## Documentation

Full documentation is available at **[gatesuite.github.io/mcpgate](https://gatesuite.github.io/mcpgate/)**.

---

© 2026 MCPGate
