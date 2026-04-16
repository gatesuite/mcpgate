.PHONY: help app-up app-down app-logs docs-up docs-down docs-logs test-run test-down clean

.DEFAULT_GOAL := help

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'


# ── MCPGate (app) ───────────────────────────────────────────────
# Uses deployments/docker-compose/docker-compose.yml which builds
# the production image from source via the local Dockerfile.
# The root docker-compose.yml (image-only, no build) is the
# zero-install file for end users who pull from GHCR.

APP_COMPOSE := deployments/docker-compose/docker-compose.yml

app-up: ## Build and start MCPGate + Postgres from source (localhost:8000)
	docker compose -f $(APP_COMPOSE) up -d --build --force-recreate

app-down: ## Stop MCPGate (volumes preserved — DB data survives)
	docker compose -f $(APP_COMPOSE) down

app-logs: ## Tail MCPGate container logs
	docker compose -f $(APP_COMPOSE) logs -f mcpgate


# ── Docs site ───────────────────────────────────────────────────

docs-up: ## Start docs dev server (localhost:4321/mcpgate/)
	cd docs && docker compose up -d

docs-down: ## Stop docs container
	cd docs && docker compose down

docs-logs: ## Tail docs container logs
	cd docs && docker compose logs -f docs


# ── E2E tests ───────────────────────────────────────────────────

test-run: ## Run E2E tests (builds test image, starts Postgres, runs pytest)
	docker compose -f docker-compose.test.yml run --rm --build test

test-down: ## Stop and remove test containers and volumes
	docker compose -f docker-compose.test.yml down -v


# ── Nuclear clean ───────────────────────────────────────────────
# Wipes containers, volumes, and caches for all stacks.

clean: ## Wipe everything — containers, volumes, caches, lockfiles
	docker compose -f $(APP_COMPOSE) down -v --remove-orphans 2>/dev/null || true
	docker compose -f docker-compose.test.yml down -v --remove-orphans 2>/dev/null || true
	cd docs && docker compose down -v --remove-orphans 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -f docs/package-lock.json
