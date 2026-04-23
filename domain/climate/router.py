from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from httpx import HTTPError
from redis.asyncio import Redis

from domain.climate.cache import ClimateHistoryCache
from domain.climate.provider import ClimateHistoryProvider
from domain.climate.schema import ClimateHistoryResponse, Granularity
from domain.climate.service import fetch_climate_history
from providers.nasapower.climate_provider import NasaPowerClimateProvider
from providers.redis.climate_cache import RedisClimateHistoryCache
from providers.redis.config import get_redis


router = APIRouter(prefix="/climate", tags=["climate"])


DAILY_MAX_DAYS = 366


def get_climate_provider() -> ClimateHistoryProvider:
    return NasaPowerClimateProvider()


def get_climate_cache(redis: Redis = Depends(get_redis)) -> ClimateHistoryCache:
    return RedisClimateHistoryCache(redis)


def _parse_iso_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {field}: expected YYYY-MM-DD ({e}).",
        )


@router.get("/history", response_model=ClimateHistoryResponse)
async def get_climate_history(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    start: str = Query(..., description="Fecha inicial YYYY-MM-DD."),
    end: str = Query(..., description="Fecha final YYYY-MM-DD."),
    granularity: Granularity = Query(
        "monthly",
        description="'monthly' (default, ergonómico para LLM) o 'daily' (máx. 366 días por request).",
    ),
    provider: ClimateHistoryProvider = Depends(get_climate_provider),
    cache: ClimateHistoryCache = Depends(get_climate_cache),
):
    "Histórico climático desde 1981 (NASA POWER, community AG): T°, precipitación, humedad, radiación solar. Cache Redis 7d."
    start_d = _parse_iso_date(start, "start")
    end_d = _parse_iso_date(end, "end")
    if end_d < start_d:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'end' must be on or after 'start'.",
        )
    if granularity == "daily" and (end_d - start_d).days > DAILY_MAX_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Daily granularity is limited to {DAILY_MAX_DAYS} days per request.",
        )

    try:
        result = await fetch_climate_history(
            provider, cache, lat, lon, start, end, granularity
        )
    except HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Climate provider error: {e}",
        )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No climate data found for the given parameters.",
        )
    return result
