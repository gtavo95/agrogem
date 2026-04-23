from fastapi import APIRouter, Depends, HTTPException, Query, status
from httpx import HTTPError
from redis.asyncio import Redis

from domain.elevation.cache import ElevationCache
from domain.elevation.provider import ElevationProvider
from domain.elevation.schema import ElevationResponse
from domain.elevation.service import fetch_elevation
from providers.openmeteo.elevation_provider import OpenMeteoElevationProvider
from providers.redis.config import get_redis
from providers.redis.elevation_cache import RedisElevationCache


router = APIRouter(prefix="/elevation", tags=["elevation"])


def get_elevation_provider() -> ElevationProvider:
    return OpenMeteoElevationProvider()


def get_elevation_cache(redis: Redis = Depends(get_redis)) -> ElevationCache:
    return RedisElevationCache(redis)


@router.get("", response_model=ElevationResponse)
async def get_elevation(
    lat: float = Query(..., ge=-90, le=90, description="Latitud"),
    lon: float = Query(..., ge=-180, le=180, description="Longitud"),
    provider: ElevationProvider = Depends(get_elevation_provider),
    cache: ElevationCache = Depends(get_elevation_cache),
):
    "Altitud (m.s.n.m) desde Open-Meteo Elevation. Cacheado 365 días (la altitud no cambia)."
    try:
        result = await fetch_elevation(provider, cache, lat, lon)
    except HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Elevation provider error: {e}",
        )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No elevation data found for coordinates.",
        )
    return result
