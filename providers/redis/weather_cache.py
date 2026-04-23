from typing import Awaitable, cast

from redis.asyncio import Redis

from domain.weather.schema import WeatherResponse


WEATHER_KEY_PREFIX = "weather:"
WEATHER_TTL_SECONDS = 15 * 60


def _weather_key(lat: float, lon: float) -> str:
    return f"{WEATHER_KEY_PREFIX}{lat:.4f}:{lon:.4f}"


class RedisWeatherCache:
    """Redis adapter for the WeatherCache port."""

    def __init__(self, redis: Redis, ttl_seconds: int = WEATHER_TTL_SECONDS):
        self._redis = redis
        self._ttl = ttl_seconds

    async def get(self, lat: float, lon: float) -> WeatherResponse | None:
        raw = await cast(
            Awaitable[str | None], self._redis.get(_weather_key(lat, lon))
        )
        if not raw:
            return None
        return WeatherResponse.model_validate_json(raw)

    async def set(self, lat: float, lon: float, weather: WeatherResponse) -> None:
        await cast(
            Awaitable[bool],
            self._redis.set(
                _weather_key(lat, lon),
                weather.model_dump_json(),
                ex=self._ttl,
            ),
        )
