---
title: Contributing
description: How to contribute to MCPGate — dev setup, tests, commit conventions, and reporting issues.
---

Thanks for taking the time to contribute to MCPGate.

## Requirements

- Docker Desktop 4.0+
- Python 3.12+
- [pre-commit](https://pre-commit.com/) — linting and formatting hooks

```bash
pip install pre-commit
pre-commit install
```

## Development setup

```bash
# 1. Clone the repo
git clone https://github.com/gatesuite/mcpgate.git
cd mcpgate

# 2. Create your credentials file
cp .env.example .env
# Edit .env — set SECRET_KEY, ADMIN_API_KEY, and other values
# Generate keys with: openssl rand -hex 32

# 3. Start the stack (MCPGate + Postgres)
make app-up
```

MCPGate will be available at **http://localhost:8000**.

## Running tests

```bash
# Run the full E2E test suite (builds test image, starts Postgres, runs pytest)
make test-run

# Tear down test containers and volumes
make test-down
```

Tests use a real PostgreSQL instance and cover key issuance, verification, revocation, and admin API endpoints.

## Pre-commit hooks

Hooks run automatically on `git commit`. To run them manually across all files:

```bash
pre-commit run --all-files
```

Hooks include: `black`, `isort`, `flake8`, `check-yaml`, `detect-private-key`.

## Make targets

| Command | Description |
|---------|-------------|
| `make app-up` | Build and start MCPGate + Postgres from source |
| `make app-down` | Stop the stack (volumes preserved) |
| `make app-logs` | Tail MCPGate container logs |
| `make test-run` | Run E2E tests |
| `make test-down` | Remove test containers and volumes |
| `make docs-up` | Start the docs dev server |
| `make clean` | Wipe all containers, volumes, and caches |

## Commit messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/) — releases and the changelog are automated via [release-please](https://github.com/googleapis/release-please).

| Prefix | When to use |
|--------|-------------|
| `feat:` | New feature or behaviour |
| `fix:` | Bug fix |
| `docs:` | Documentation changes only |
| `chore:` | CI, deps, tooling — no user-facing change |
| `test:` | Adding or fixing tests |
| `refactor:` | Internal restructure, no behaviour change |

Breaking changes: add `!` after the type (`feat!:`) and include a `BREAKING CHANGE:` footer in the commit body.

## Pull requests

1. Fork and branch off `main`.
2. Keep PRs focused — one logical change per PR.
3. Ensure `pre-commit run --all-files` and `make test-run` pass locally before pushing.
4. Fill in the PR description — what changed and why.

## Reporting issues

Use the GitHub issue templates — they prompt for the information needed to reproduce the problem.

- [Bug report](https://github.com/gatesuite/mcpgate/issues/new?template=bug_report.md)
- [Feature request](https://github.com/gatesuite/mcpgate/issues/new?template=feature_request.md)

Include your OS, Docker version, MCPGate version, deployment method, and the exact steps to reproduce.
