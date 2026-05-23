import json
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class RedisCache:
    """Redis cache wrapper with async operations."""

    _instance: Optional[aioredis.Redis] = None

    @classmethod
    async def get_client(cls) -> aioredis.Redis:
        if cls._instance is None:
            cls._instance = aioredis.from_url(settings.redis_url, decode_responses=True)
        return cls._instance

    @classmethod
    async def close(cls) -> None:
        if cls._instance:
            await cls._instance.close()
            cls._instance = None

    @staticmethod
    async def get(key: str) -> Optional[str]:
        client = await RedisCache.get_client()
        return await client.get(key)

    @staticmethod
    async def set(key: str, value: str, expire: Optional[int] = None) -> None:
        client = await RedisCache.get_client()
        await client.set(key, value, ex=expire)

    @staticmethod
    async def delete(key: str) -> None:
        client = await RedisCache.get_client()
        await client.delete(key)

    @staticmethod
    async def get_json(key: str) -> Optional[dict]:
        raw = await RedisCache.get(key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in cache key {key}")
        return None

    @staticmethod
    async def set_json(key: str, value: dict, expire: Optional[int] = None) -> None:
        await RedisCache.set(key, json.dumps(value, default=str), expire=expire)
