---
title: Deployment
description: Deploy MCPGate with Docker Compose for local/small setups, or Helm for Kubernetes production deployments.
---

## Docker Compose (local / small deployments)

The root `docker-compose.yml` is the zero-config deployment for end users. It pulls the pre-built image from GHCR and bundles a PostgreSQL 16 database:

```bash
curl -O https://raw.githubusercontent.com/gatesuite/mcpgate/main/docker-compose.yml
```

Set required environment variables:

```bash
export ADMIN_API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export DATABASE_URL=postgresql+asyncpg://mcpgate:mcpgate@postgres:5432/mcpgate
```

Start:

```bash
docker compose up -d
```

MCPGate will be available at `http://localhost:8000`.

### Pin to a release

```bash
MCPGATE_VERSION=1.2.3 docker compose up -d
```

Or in `.env`:

```
MCPGATE_VERSION=1.2.3
ADMIN_API_KEY=your-secret-here
DATABASE_URL=postgresql+asyncpg://mcpgate:mcpgate@postgres:5432/mcpgate
KEY_PREFIX=mcp_sk_
```

---

## Build from source

To build and run from the local source (useful when developing MCPGate itself):

```bash
make app-up    # builds production image, starts MCPGate + Postgres
make app-logs  # tail logs
make app-down  # stop (volumes preserved)
```

This uses `deployments/docker-compose/docker-compose.yml` which builds the `production` Dockerfile target.

---

## Kubernetes with Helm

MCPGate ships a Helm chart published to GHCR as an OCI artifact.

### Install

```bash
helm install mcpgate oci://ghcr.io/gatesuite/charts/mcpgate \
  --namespace mcpgate \
  --create-namespace \
  --set secret.adminApiKey="your-strong-secret-here" \
  --set secret.databaseUrl="postgresql+asyncpg://user:pass@postgres:5432/mcpgate"
```

### Key Helm values

| Value | Default | Description |
|-------|---------|-------------|
| `replicaCount` | `1` | Number of pods |
| `image.repository` | `ghcr.io/gatesuite/mcpgate` | Container image |
| `image.tag` | `latest` | Image tag — pin to a release in production |
| `secret.adminApiKey` | `""` | Master admin key (**required**) |
| `secret.databaseUrl` | `""` | PostgreSQL connection string (**required**) |
| `secret.keyPrefix` | `mcp_sk_` | Key prefix |
| `service.port` | `8000` | Service port |
| `autoscaling.enabled` | `true` | Enable HPA |
| `autoscaling.minReplicas` | `1` | Minimum replicas |
| `autoscaling.maxReplicas` | `10` | Maximum replicas |
| `autoscaling.targetCPUUtilizationPercentage` | `70` | CPU scale trigger |
| `pdb.enabled` | `false` | Enable PodDisruptionBudget |
| `ingress.enabled` | `false` | Enable ingress |

### With an existing database

MCPGate expects an async-compatible PostgreSQL connection string (`postgresql+asyncpg://`). It auto-creates the `api_keys` table on startup.

```yaml
secret:
  adminApiKey: "your-strong-secret"
  databaseUrl: "postgresql+asyncpg://mcpgate:password@my-postgres-host:5432/mcpgate"
```

### Ingress example (NGINX + cert-manager)

```yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: keys.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: mcpgate-tls
      hosts:
        - keys.yourdomain.com
```

---

## Production checklist

- [ ] `ADMIN_API_KEY` is at least 32 random bytes, stored in a secret manager (not in source control)
- [ ] Image is pinned to a specific version tag, not `latest`
- [ ] MCPGate is not exposed publicly — behind a private load balancer or accessed only by your backend services
- [ ] PostgreSQL has a dedicated user with minimal privileges (`SELECT`, `INSERT`, `UPDATE`, `DELETE` on `api_keys` only)
- [ ] TLS is terminated at the ingress/load balancer
- [ ] `replicaCount` ≥ 2 in production, with `pdb.enabled: true` to prevent simultaneous pod eviction
- [ ] Resource limits are set (defaults: 250m CPU / 128Mi memory)
- [ ] Liveness, readiness, and startup probes are enabled (on by default in the Helm chart)
- [ ] Log shipping is configured — MCPGate logs to stdout at INFO level

---

## Environment variables reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL async connection string (`postgresql+asyncpg://...`) |
| `ADMIN_API_KEY` | ✅ | — | Master token for admin endpoints |
| `KEY_PREFIX` | — | `mcp_sk_` | Prefix for generated keys |
| `PROJECT_NAME` | — | `MCPGate` | Service name in API responses |
| `VERSION` | — | `1.0.0` | Version string |
| `API_V1_STR` | — | `/api/v1` | API route prefix |
