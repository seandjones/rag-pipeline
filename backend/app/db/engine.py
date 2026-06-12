from functools import cache
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


@cache
def get_engine():
    """Create the async engine once on first call. Safe to import at module level."""
    settings = get_settings()
    return create_async_engine(
        settings.async_database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        # Disable SSL negotiation — the pgvector Docker image doesn't have SSL configured.
        # Without this asyncpg tries SSL first and raises a confusing ConnectionRefusedError.
        connect_args={"ssl": False},
    )


@cache
def _session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


def AsyncSessionLocal() -> AsyncSession:
    """Return a new AsyncSession. Use as: async with AsyncSessionLocal() as s: ..."""
    return _session_factory()()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory()() as session:
        yield session
