from fastapi import APIRouter, Depends, HTTPException, Query, status
from httpx import HTTPError
from redis.asyncio import Redis

from domain.soil.cache import SoilCache
from domain.soil.provider import SoilProvider
from domain.soil.schema import SoilResponse
from domain.soil.service import fetch_soil
from providers.redis.config import get_redis
from providers.redis.soil_cache import RedisSoilCache
from providers.soilgrids.soil_provider import SoilGridsSoilProvider


router = APIRouter(prefix="/soil", tags=["soil"])


def get_soil_provider() -> SoilProvider:
    return SoilGridsSoilProvider()


def get_soil_cache(redis: Redis = Depends(get_redis)) -> SoilCache:
    return RedisSoilCache(redis)


@router.get("", response_model=SoilResponse)
async def get_soil(
    lat: float = Query(..., ge=-90, le=90, description="Latitud"),
    lon: float = Query(..., ge=-180, le=180, description="Longitud"),
    provider: SoilProvider = Depends(get_soil_provider),
    cache: SoilCache = Depends(get_soil_cache),
):
    "Perfil de suelo en zona radicular (0-5, 5-15, 15-30 cm) desde ISRIC SoilGrids: pH, SOC, N, textura USDA, CEC. Cacheado 90 días."
    try:
        result = await fetch_soil(provider, cache, lat, lon)
    except HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Soil provider error: {e}",
        )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No soil data found for coordinates.",
        )
    return result
