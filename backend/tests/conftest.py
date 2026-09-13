import asyncio
import os
import subprocess
import sys
import tempfile
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Settings are read once, at import time, so the test environment has to be in
# place before anything under app/ is imported.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("AUTH_MODE", "local")
os.environ.setdefault("SECRET_KEY", "test-secret-not-used-anywhere-real")
# The default (/storage) is only writable inside the app container; give the
# host-run suite its own throwaway directory for attachment uploads.
os.environ.setdefault("STORAGE_PATH", tempfile.mkdtemp(prefix="rodiva-test-storage-"))

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import dispose_engine  # noqa: E402
from app.main import app  # noqa: E402

TEST_PASSWORD = "a-long-enough-password"

RegisterFn = Callable[..., Awaitable[tuple[AsyncClient, dict[str, Any]]]]


def _database_reachable() -> bool:
    async def ping() -> bool:
        engine = create_async_engine(get_settings().database_url)
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:
            return False
        finally:
            await engine.dispose()
        return True

    return asyncio.run(ping())


@pytest.fixture(scope="session")
def database() -> None:
    """Rebuild the schema from the migrations, then hand control back.

    Going through Alembic rather than `create_all` means the suite runs against
    the schema the deployment actually gets, so model/migration drift fails
    the tests.
    """
    database_name = make_url(get_settings().database_url).database or ""
    if not database_name.endswith("_test"):
        pytest.skip("refusing to rebuild a database whose name does not end in _test")
    if not _database_reachable():
        pytest.skip("no database reachable at DATABASE_URL")
    for arguments in (["downgrade", "base"], ["upgrade", "head"]):
        subprocess.run(
            [sys.executable, "-m", "alembic", *arguments],
            cwd=BACKEND_DIR,
            check=True,
            capture_output=True,
        )


@pytest.fixture(autouse=True)
async def _fresh_engine() -> AsyncIterator[None]:
    """Drop the cached engine between tests.

    Each test runs in its own event loop, and a connection pool outlives
    neither: reusing it raises "Event loop is closed" on the next test that
    touches the DB.
    """
    yield
    await dispose_engine()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def register(database: None) -> AsyncIterator[RegisterFn]:
    """Register a fresh account + household and hand back a client already
    holding its session cookie. Every test gets its own household, so
    household-scoped data cannot leak between tests.
    """
    clients: list[AsyncClient] = []

    async def factory(**extra: Any) -> tuple[AsyncClient, dict[str, Any]]:
        ac = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        clients.append(ac)
        payload = {
            "email": f"{uuid.uuid4().hex}@example.com",
            "password": TEST_PASSWORD,
            "household_name": "Test household",
            **extra,
        }
        response = await ac.post("/auth/register", json=payload)
        assert response.status_code == 201, response.text
        return ac, response.json()

    yield factory

    for ac in clients:
        await ac.aclose()


@pytest.fixture
async def user_client(register: RegisterFn) -> AsyncClient:
    ac, _ = await register()
    return ac
