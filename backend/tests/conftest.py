"""Shared test setup.

The environment is set before anything imports `app`, because `app.config.get_settings()`
and `app.db.engine.get_engine()` are cached the first time they are called.
"""

import asyncio
import os
from urllib.parse import urlsplit

import pytest

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ragdemo_test"
)
_TEST_DB_NAME = urlsplit(TEST_DATABASE_URL).path.lstrip("/")
# Guard: the integration fixtures truncate tables, so never point them at a real database.
assert _TEST_DB_NAME.endswith("_test"), "TEST_DATABASE_URL must name a database ending in _test"

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["OPENAI_API_KEY"] = "test-key-not-used"

import asyncpg  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import DBAPIError  # noqa: E402

from app.db.engine import AsyncSessionLocal, get_engine  # noqa: E402
from app.db.migrations import ensure_schema  # noqa: E402


class _DatabaseUnusable(Exception):
    """Raised when the target Postgres server cannot be used for the test database."""


async def _prepare_database() -> None:
    admin_url = urlsplit(TEST_DATABASE_URL)._replace(path="/postgres").geturl()
    conn = await asyncpg.connect(admin_url, ssl=False)
    try:
        has_pgvector = await conn.fetchval(
            "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"
        )
        if not has_pgvector:
            raise _DatabaseUnusable("this server does not have the pgvector extension")
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", _TEST_DB_NAME)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{_TEST_DB_NAME}"')
    finally:
        await conn.close()
    try:
        await ensure_schema()
    finally:
        await get_engine().dispose()


@pytest.fixture(scope="session")
def database() -> str:
    """Create the test database and schema once per run, or skip if Postgres is unavailable."""
    try:
        asyncio.run(_prepare_database())
    except (OSError, asyncpg.PostgresError, DBAPIError, _DatabaseUnusable) as exc:
        message = f"Postgres with pgvector is not usable at {TEST_DATABASE_URL}: {exc}"
        # CI sets REQUIRE_DATABASE=1 so a broken database fails the build instead of skipping.
        if os.environ.get("REQUIRE_DATABASE") == "1":
            pytest.fail(message)
        pytest.skip(message)
    return TEST_DATABASE_URL


@pytest.fixture
async def db_session(database):
    """An empty document_chunks table and a session on it.

    The engine is disposed afterwards because asyncpg connections belong to the event loop that
    opened them, and each test runs in its own loop.
    """
    async with get_engine().begin() as conn:
        await conn.execute(text("TRUNCATE document_chunks RESTART IDENTITY"))
    async with AsyncSessionLocal() as session:
        yield session
    await get_engine().dispose()
