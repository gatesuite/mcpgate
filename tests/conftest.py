"""
Test fixtures for MCPGate E2E tests.

DATABASE_URL, ADMIN_API_KEY, and MCPGATE_TEST must be set before any
app.* imports because app/core/database.py initialises the engine at
import time. With MCPGATE_TEST=1, database.py uses NullPool so asyncpg
connections are never held across per-test event loops.
"""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://mcpgate:mcpgate@localhost:5432/mcpgate_test",
)
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("MCPGATE_TEST", "1")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

# ---------------------------------------------------------------------------
# HTTP client — function-scoped, one event loop per test.
#
# httpx.ASGITransport does NOT send ASGI lifespan events, so the app's
# lifespan startup (create_all) never runs automatically. We replicate
# startup here before yielding the client.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as c:
        yield c
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM api_keys"))


# ---------------------------------------------------------------------------
# Admin auth headers — matches ADMIN_API_KEY set above.
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_headers():
    return {"Authorization": "Bearer test-admin-key"}
