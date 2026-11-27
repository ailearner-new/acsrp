"""Redis connection and client management."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from backend.app.core.config import settings


class RedisManager:
    """Manages Redis connection pool and client."""

    def __init__(self):
        self._client: Optional[Redis] = None

    @property
    def client(self) -> Redis:
        if self._client is None:
            self._client = redis.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                decode_responses=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    @asynccontextmanager
    async def get_client(self) -> AsyncGenerator[Redis, None]:
        """Get a Redis client."""
        yield self.client


# Global Redis manager
redis_manager = RedisManager()


async def get_redis() -> AsyncGenerator[Redis, None]:
    """FastAPI dependency for Redis client."""
    async with redis_manager.get_client() as client:
        yield client


async def init_redis() -> None:
    """Initialize Redis connection (test connection)."""
    client = redis_manager.client
    await client.ping()


async def close_redis() -> None:
    """Close Redis connections."""
    await redis_manager.close()