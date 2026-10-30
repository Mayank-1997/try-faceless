"""Async SQLAlchemy engine and session factory.

Provides:
- ``engine``: a single async engine with connection pooling.
- ``AsyncSessionLocal``: an ``async_sessionmaker`` for creating sessions.
- ``get_db_session``: a FastAPI dependency that yields a scoped session.

Usage in routers::

    @router.get("/items")
    async def list_items(db: AsyncSession = Depends(get_db_session)):
        ...

Usage in services (non-FastAPI)::

    async with AsyncSessionLocal() as session:
        ...
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import get_settings

settings = get_settings()

_is_sqlite = settings.database.url.startswith("sqlite")

_engine_kwargs: dict = {
    "echo": settings.database.echo,
    "pool_pre_ping": not _is_sqlite,
}

if not _is_sqlite:
    _engine_kwargs["pool_size"] = settings.database.pool_size
    _engine_kwargs["max_overflow"] = settings.database.max_overflow
    _engine_kwargs["pool_recycle"] = 3600

engine: AsyncEngine = create_async_engine(
    settings.database.url,
    **_engine_kwargs,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a scoped async database session.

    The session is automatically closed when the request completes.
    If an exception occurs, the transaction is rolled back.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def dispose_engine() -> None:
    """Dispose of the engine connection pool — call on application shutdown."""
    await engine.dispose()
