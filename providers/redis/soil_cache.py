from typing import Awaitable, cast

from redis.asyncio import Redis

from domain.soil.schema import SoilResponse


SOIL_TTL_SECONDS = 90 * 24 * 60 * 60
SOIL_KEY_PREFIX = "soil:"


def _soil_key(lat: float, lon: float) -> str:
    return f"{SOIL_KEY_PREFIX}{lat:.4f}:{lon:.4f}"


class RedisSoilCache:
    """Redis adapter for the SoilCache port."""

    def __init__(self, redis: Redis, ttl_seconds: int = SOIL_TTL_SECONDS):
        self._redis = redis
        self._ttl = ttl_seconds

    async def get(self, lat: float, lon: float) -> SoilResponse | None:
        raw = await cast(
            Awaitable[str | None], self._redis.get(_soil_key(lat, lon))
        )
        if not raw:
            return None
        return SoilResponse.model_validate_json(raw)

    async def set(self, lat: float, lon: float, result: SoilResponse) -> None:
        await cast(
            Awaitable[bool],
            self._redis.set(
                _soil_key(lat, lon),
                result.model_dump_json(),
                ex=self._ttl,
            ),
        )
