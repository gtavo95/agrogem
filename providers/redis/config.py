from typing import Awaitable, cast

import redis
import redis.asyncio as aioredis
from fastapi import Request
from redis.asyncio import Redis


def get_client(url: str):
    return redis.from_url(url, decode_responses=True)


def get_async_client(url: str) -> Redis:
    return aioredis.from_url(url, decode_responses=True)


def get_redis(request: Request) -> Redis:
    """Dependency to retrieve the async Redis client from app state."""
    return request.app.state.redis


async def ping(client: Redis) -> bool:
    return await cast(Awaitable[bool], client.ping())


async def aclose(client: Redis) -> None:
    await cast(Awaitable[None], client.aclose())
