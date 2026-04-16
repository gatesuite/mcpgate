---
title: Architecture
description: Tech stack, project structure, and request flow diagrams for MCPGate.
---

## Tech stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Web framework | FastAPI 0.115 | Async-first, automatic OpenAPI, high performance |
| ORM | SQLAlchemy 2.0 (async) | Async sessions, declarative models |
| Database driver | asyncpg 0.30 | Native async PostgreSQL — no thread pool overhead |
| Validation | Pydantic v2 | Fast, strict, automatic API docs |
| Hashing | bcrypt 4.x + hashlib | Industry-standard password hashing with SHA-256 pre-hash |
| Server | Uvicorn | ASGI server with uvloop |
| Database | PostgreSQL 16 | ACID-compliant, excellent indexing |
| Runtime | Python 3.12 | Latest stable, pre-built wheels for all dependencies |
| Container | Docker (python:3.12-slim) | Minimal attack surface |
| Orchestration | Helm (OCI) | Kubernetes-native deployment |

---

## Project structure

```
mcpgate/
├── app/
│   ├── main.py              # FastAPI app, lifespan (table creation), CORS, router
│   ├── api/
│   │   └── routes.py        # All 5 endpoints: create, list, delete, verify, (health in main)
│   ├── core/
│   │   ├── config.py        # Settings via pydantic-settings + .env
│   │   ├── database.py      # SQLAlchemy engine, session factory, NullPool for tests
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
│   ├── docker-compose/
│   │   └── docker-compose.yml  # Build-from-source compose (make app-up)
│   └── helm/mcpgate/           # Helm chart for Kubernetes
├── docs/                    # This documentation site (Astro/Starlight)
├── Dockerfile               # Multi-stage: production + test targets
├── docker-compose.yml       # End-user zero-config deploy (pulls from GHCR)
├── docker-compose.test.yml  # Test runner (make test-run)
├── Makefile                 # app-*, docs-*, test-* targets
├── requirements.txt         # Runtime dependencies
├── requirements-test.txt    # Test-only dependencies
└── pytest.ini               # asyncio_mode = auto
```

---

## Database schema

```sql
CREATE TABLE api_keys (
    id          TEXT PRIMARY KEY,          -- UUID string
    public_id   TEXT NOT NULL UNIQUE,      -- Indexed — O(1) lookup
    key_hash    TEXT NOT NULL,             -- bcrypt(sha256(plain_key))
    prefix      TEXT NOT NULL,             -- mcp_sk_<id>_...<last4> — safe to display
    user_id     TEXT NOT NULL,             -- Indexed — list by user
    name        TEXT,
    scopes      JSONB,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    expires_at  TIMESTAMPTZ
);

CREATE INDEX ix_api_keys_public_id ON api_keys (public_id);
CREATE INDEX ix_api_keys_user_id   ON api_keys (user_id);
```

Tables are created automatically on startup via SQLAlchemy's `create_all`.

---

## Request flow

### Key creation

```
POST /api/v1/keys
      │
      ▼
verify_admin_key()              check Authorization: Bearer header
      │
      ▼
generate_api_key(prefix)        token_hex(8) + token_hex(32)
      │                         sha256(plain_key) → bcrypt → key_hash
      ▼
INSERT INTO api_keys (...)       store public_id + hash, never plain key
      │
      ▼
return ApiKeyResponseWithSecret  key shown once only
```

### Key verification (hot path)

```
POST /api/v1/verify
      │
      ▼
extract public_id               key[len(prefix):].split("_")[0]
      │
      ▼
SELECT WHERE public_id = ?      single indexed read — O(1)
AND is_active = TRUE
      │
      ▼
bcrypt.checkpw(                 constant-time comparison
  sha256(incoming_key),
  stored_hash
)
      │
      ▼
check expires_at < now()
      │
      ▼
UPDATE last_used_at = now()
      │
      ▼
return VerifyResponse
```

---

## Kubernetes topology

```
                    ┌─────────────────────────────────────────┐
                    │  Kubernetes Cluster                      │
                    │                                          │
  Your Backend ────▶│  Service (ClusterIP :8000)              │
  MCP Servers  ────▶│       │                                 │
                    │       ▼                                  │
                    │  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
                    │  │  Pod 1  │  │  Pod 2  │  │  Pod N  │ │
                    │  │mcpgate  │  │mcpgate  │  │mcpgate  │ │
                    │  └────┬────┘  └────┬────┘  └────┬────┘ │
                    │       └─────┬──────┘            │      │
                    │             ▼                    │      │
                    │        PostgreSQL ◀──────────────┘      │
                    │                                          │
                    │  HPA: 1–10 replicas (70% CPU / 80% mem) │
                    │  PDB: max 1 unavailable                  │
                    └─────────────────────────────────────────┘
```

---

## Multi-stage Docker build

The Dockerfile has two targets:

| Target | Used by | Contents |
|--------|---------|----------|
| `production` | `docker-compose.yml`, Helm | `requirements.txt` + `app/` only. Non-root user, minimal image. |
| `test` | `docker-compose.test.yml` | `requirements.txt` + `requirements-test.txt` + `app/` + `tests/` + `pytest.ini`. Runs pytest. |

The test image is never pushed to GHCR — it's only used locally and in CI via `docker compose -f docker-compose.test.yml`.
