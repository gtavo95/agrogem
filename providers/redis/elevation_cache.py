from typing import Awaitable, cast

from redis.asyncio import Redis

from domain.elevation.schema import ElevationResponse


ELEVATION_TTL_SECONDS = 365 * 24 * 60 * 60
ELEVATION_KEY_PREFIX = "elevation:"


def _elevation_key(lat: float, lon: float) -> str:
    return f"{ELEVATION_KEY_PREFIX}{lat:.4f}:{lon:.4f}"


class RedisElevationCache:
    """Redis adapter for the ElevationCache port."""

    def __init__(self, redis: Redis, ttl_seconds: int = ELEVATION_TTL_SECONDS):
        self._redis = redis
        self._ttl = ttl_seconds

    async def get(self, lat: float, lon: float) -> ElevationResponse | None:
        raw = await cast(
            Awaitable[str | None], self._redis.get(_elevation_key(lat, lon))
        )
        if not raw:
            return None
        return ElevationResponse.model_validate_json(raw)

    async def set(
        self, lat: float, lon: float, result: ElevationResponse
    ) -> None:
        await cast(
            Awaitable[bool],
            self._redis.set(
                _elevation_key(lat, lon),
                result.model_dump_json(),
                ex=self._ttl,
            ),
        )
