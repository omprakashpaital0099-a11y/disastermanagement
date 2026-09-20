import redis.asyncio as redis

from app.core.config import get_settings



class LocalCache:
    async def get(self, key: str) -> None:
        return None

    async def setex(self, key: str, seconds: int, value: str) -> None:
        return None

    async def scan_iter(self, match: str):
        if False:
            yield match

    async def aclose(self) -> None:
        return None


redis_url = get_settings().redis_url
client = redis.from_url(redis_url, decode_responses=True) if redis_url else LocalCache()


async def invalidate_hazard_cache() -> None:
    async for key in client.scan_iter(match="hazards:*"):
        await client.delete(key)


async def close_cache() -> None:
    await client.aclose()
