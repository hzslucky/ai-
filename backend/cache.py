"""Caching layer with Redis + in-memory fallback."""

import hashlib
import json
from typing import Optional

import redis.asyncio as aioredis

from config import settings


class InMemoryCache:
    """Simple in-memory cache for development when Redis is unavailable."""

    def __init__(self):
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    async def set(self, key: str, value: str, expire: int = 3600) -> None:
        self._store[key] = value

    async def exists(self, key: str) -> bool:
        return key in self._store


class RedisCache:
    """Redis-backed cache for production."""

    def __init__(self, url: str):
        self._redis: Optional[aioredis.Redis] = None
        self._url = url

    async def _ensure_connected(self):
        if self._redis is None:
            self._redis = await aioredis.from_url(self._url, decode_responses=True)

    async def get(self, key: str) -> Optional[str]:
        await self._ensure_connected()
        return await self._redis.get(key)

    async def set(self, key: str, value: str, expire: int = 3600) -> None:
        await self._ensure_connected()
        await self._redis.set(key, value, ex=expire)

    async def exists(self, key: str) -> bool:
        await self._ensure_connected()
        return await self._redis.exists(key) > 0


_cache_backend: Optional[InMemoryCache | RedisCache] = None


def _make_key(resume_text: str, job_description: str | None = None) -> str:
    """Generate cache key from resume content hash."""
    digest = hashlib.sha256(resume_text.encode()).hexdigest()[:16]
    if job_description:
        jd_digest = hashlib.sha256(job_description.encode()).hexdigest()[:8]
        return f"resume:{digest}:match:{jd_digest}"
    return f"resume:{digest}"


async def get_cache() -> InMemoryCache | RedisCache:
    global _cache_backend
    if _cache_backend is None:
        if settings.cache_enabled:
            try:
                backend = RedisCache(settings.redis_url)
                await backend._ensure_connected()
                _cache_backend = backend
            except Exception:
                _cache_backend = InMemoryCache()
        else:
            _cache_backend = InMemoryCache()
    return _cache_backend


async def get_cached_result(resume_text: str, job_description: str | None = None) -> Optional[dict]:
    """Retrieve cached analysis result if available."""
    cache = await get_cache()
    key = _make_key(resume_text, job_description)
    data = await cache.get(key)
    if data:
        return json.loads(data)
    return None


async def set_cached_result(resume_text: str, result: dict, job_description: str | None = None) -> None:
    """Store analysis result in cache."""
    cache = await get_cache()
    key = _make_key(resume_text, job_description)
    await cache.set(key, json.dumps(result, ensure_ascii=False))
