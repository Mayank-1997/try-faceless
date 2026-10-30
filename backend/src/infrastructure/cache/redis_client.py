"""Redis async client for caching, rate limiting, and pub/sub.

Provides a singleton ``Redis`` client configured from application settings.
Use ``get_redis()`` for dependency injection in FastAPI routes and
``get_redis_client()`` for direct access in services.
"""

from __future__ import annotations

from redis.asyncio import Redis, from_url

from src.core.config import get_settings

_redis_client: Redis | None = None


def get_redis_client() -> Redis:
    """Return a cached async Redis client singleton.

    The client is lazily initialised on first call and reused for the
    lifetime of the process.
    """
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = from_url(
            settings.redis.url,
            decode_responses=True,
            encoding="utf-8",
            max_connections=50,
        )
    return _redis_client


async def get_redis() -> Redis:
    """FastAPI dependency that yields the Redis client."""
    return get_redis_client()


async def close_redis() -> None:
    """Close the Redis connection pool — call on application shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
