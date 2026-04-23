from typing import Awaitable, cast

from redis.asyncio import Redis

from domain.geocoding.schema import GeocodeResult, ReverseGeocodeResult


GEOCODE_TTL_SECONDS = 30 * 24 * 60 * 60
FORWARD_KEY_PREFIX = "geocode:fwd:"
REVERSE_KEY_PREFIX = "geocode:rev:"


def _normalize_query(query: str) -> str:
    return query.strip().lower()


def _forward_key(query: str, country: str | None) -> str:
    country_part = country.upper() if country else "ANY"
    return f"{FORWARD_KEY_PREFIX}{country_part}:{_normalize_query(query)}"


def _reverse_key(lat: float, lon: float) -> str:
    return f"{REVERSE_KEY_PREFIX}{lat:.4f}:{lon:.4f}"


class RedisGeocodingCache:
    """Redis adapter for the GeocodingCache port."""

    def __init__(self, redis: Redis, ttl_seconds: int = GEOCODE_TTL_SECONDS):
        self._redis = redis
        self._ttl = ttl_seconds

    async def get_forward(
        self, query: str, country: str | None
    ) -> GeocodeResult | None:
        raw = await cast(
            Awaitable[str | None], self._redis.get(_forward_key(query, country))
        )
        if not raw:
            return None
        return GeocodeResult.model_validate_json(raw)

    async def set_forward(
        self, query: str, country: str | None, result: GeocodeResult
    ) -> None:
        await cast(
            Awaitable[bool],
            self._redis.set(
                _forward_key(query, country),
                result.model_dump_json(),
                ex=self._ttl,
            ),
        )

    async def get_reverse(
        self, lat: float, lon: float
    ) -> ReverseGeocodeResult | None:
        raw = await cast(
            Awaitable[str | None], self._redis.get(_reverse_key(lat, lon))
        )
        if not raw:
            return None
        return ReverseGeocodeResult.model_validate_json(raw)

    async def set_reverse(
        self, lat: float, lon: float, result: ReverseGeocodeResult
    ) -> None:
        await cast(
            Awaitable[bool],
            self._redis.set(
                _reverse_key(lat, lon),
                result.model_dump_json(),
                ex=self._ttl,
            ),
        )
