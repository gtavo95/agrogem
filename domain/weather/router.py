from fastapi import APIRouter, Depends, HTTPException, Query, status
from httpx import HTTPError
from redis.asyncio import Redis

from domain.weather.cache import WeatherCache
from domain.weather.provider import WeatherProvider
from domain.weather.schema import WeatherResponse
from domain.weather.service import fetch_weather
from providers.openmeteo.weather_provider import OpenMeteoWeatherProvider
from providers.redis.config import get_redis
from providers.redis.weather_cache import RedisWeatherCache


router = APIRouter(prefix="/weather", tags=["weather"])


def get_weather_provider() -> WeatherProvider:
    return OpenMeteoWeatherProvider()


def get_weather_cache(redis: Redis = Depends(get_redis)) -> WeatherCache:
    return RedisWeatherCache(redis)


@router.get("", response_model=WeatherResponse)
async def get_weather(
    lat: float = Query(..., ge=-90, le=90, description="Latitud"),
    lon: float = Query(..., ge=-180, le=180, description="Longitud"),
    provider: WeatherProvider = Depends(get_weather_provider),
    cache: WeatherCache = Depends(get_weather_cache),
):
    "Clima actual + pronóstico horario y diario (7 días) desde Open-Meteo. Cacheado en Redis por 15 minutos por coordenada."
    try:
        return await fetch_weather(provider, cache, lat, lon)
    except HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Weather provider error: {e}",
        )
