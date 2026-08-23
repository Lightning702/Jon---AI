from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from app.core.config import get_settings

_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()
_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = asyncio.Lock()
_last_call: dict[str, float] = {}
_rate_lock = asyncio.Lock()


def user_agent() -> str:
    settings = get_settings()
    return settings.maps_user_agent or f"Jon/{settings.app_version}"


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        async with _client_lock:
            if _client is None or _client.is_closed:
                _client = httpx.AsyncClient(
                    timeout=httpx.Timeout(20.0, connect=8.0),
                    follow_redirects=True,
                    headers={
                        "User-Agent": user_agent(),
                        "Accept-Language": "de,en;q=0.7",
                    },
                )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


async def throttle(bucket: str, min_interval: float) -> None:
    async with _rate_lock:
        now = time.monotonic()
        previous = _last_call.get(bucket, 0.0)
        wait = min_interval - (now - previous)
        if wait > 0:
            await asyncio.sleep(wait)
            now = time.monotonic()
        _last_call[bucket] = now


async def cached(key: str, ttl: float):
    async with _cache_lock:
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < ttl:
            return hit[1]
    return None


async def store(key: str, value: Any) -> None:
    async with _cache_lock:
        if len(_cache) > 400:
            oldest = sorted(_cache.items(), key=lambda kv: kv[1][0])[:120]
            for old_key, _ in oldest:
                _cache.pop(old_key, None)
        _cache[key] = (time.monotonic(), value)


async def get_json(
    url: str,
    params: dict[str, Any] | None = None,
    ttl: float = 300.0,
    bucket: str = "",
    min_interval: float = 0.0,
    headers: dict[str, str] | None = None,
) -> Any:
    key = f"{url}?{sorted((params or {}).items())}"
    hit = await cached(key, ttl)
    if hit is not None:
        return hit
    if bucket and min_interval:
        await throttle(bucket, min_interval)
    client = await get_client()
    response = await client.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    await store(key, data)
    return data


async def post_json(
    url: str,
    payload: Any = None,
    data: str | None = None,
    ttl: float = 300.0,
    bucket: str = "",
    min_interval: float = 0.0,
    headers: dict[str, str] | None = None,
) -> Any:
    key = f"POST {url} {payload if payload is not None else data}"
    hit = await cached(key, ttl)
    if hit is not None:
        return hit
    if bucket and min_interval:
        await throttle(bucket, min_interval)
    client = await get_client()
    if payload is not None:
        response = await client.post(url, json=payload, headers=headers)
    else:
        response = await client.post(url, content=data, headers=headers)
    response.raise_for_status()
    result = response.json()
    await store(key, result)
    return result
