"""Redis client management for shared state storage."""
from __future__ import annotations

from typing import Optional

from redis.asyncio import Redis

from core.config import get_settings

_redis_client: Optional[Redis] = None


def get_redis() -> Redis:
    """Get initialized Redis client."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _redis_client


async def init_redis() -> None:
    """Validate Redis connection on startup."""
    redis = get_redis()
    await redis.ping()


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
