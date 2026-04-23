from typing import Awaitable, cast

from redis.asyncio import Redis

from domain.climate.schema import ClimateHistoryResponse, Granularity


CLIMATE_TTL_SECONDS = 7 * 24 * 60 * 60
CLIMATE_KEY_PREFIX = "climate:hist:"


def _climate_key(
    lat: float,
    lon: float,
    start: str,
    end: str,
    granularity: Granularity,
) -> str:
    return f"{CLIMATE_KEY_PREFIX}{granularity}:{lat:.4f}:{lon:.4f}:{start}:{end}"


class RedisClimateHistoryCache:
    """Redis adapter for the ClimateHistoryCache port."""

    def __init__(self, redis: Redis, ttl_seconds: int = CLIMATE_TTL_SECONDS):
        self._redis = redis
        self._ttl = ttl_seconds

    async def get(
        self,
        lat: float,
        lon: float,
        start: str,
        end: str,
        granularity: Granularity,
    ) -> ClimateHistoryResponse | None:
        raw = await cast(
            Awaitable[str | None],
            self._redis.get(_climate_key(lat, lon, start, end, granularity)),
        )
        if not raw:
            return None
        return ClimateHistoryResponse.model_validate_json(raw)

    async def set(
        self,
        lat: float,
        lon: float,
        start: str,
        end: str,
        granularity: Granularity,
        result: ClimateHistoryResponse,
    ) -> None:
        await cast(
            Awaitable[bool],
            self._redis.set(
                _climate_key(lat, lon, start, end, granularity),
                result.model_dump_json(),
                ex=self._ttl,
            ),
        )
