from fastapi import APIRouter, Depends, HTTPException, Query, status
from httpx import HTTPError

from domain.elevation.cache import ElevationCache
from domain.elevation.provider import ElevationProvider
from domain.elevation.router import get_elevation_cache, get_elevation_provider
from domain.frost_risk.schema import FrostRiskResponse
from domain.frost_risk.service import compute_frost_risk
from domain.weather.cache import WeatherCache
from domain.weather.provider import WeatherProvider
from domain.weather.router import get_weather_cache, get_weather_provider


router = APIRouter(prefix="/frost-risk", tags=["frost-risk"])


@router.get("", response_model=FrostRiskResponse)
async def get_frost_risk(
    lat: float = Query(..., ge=-90, le=90, description="Latitud"),
    lon: float = Query(..., ge=-180, le=180, description="Longitud"),
    weather_provider: WeatherProvider = Depends(get_weather_provider),
    weather_cache: WeatherCache = Depends(get_weather_cache),
    elevation_provider: ElevationProvider = Depends(get_elevation_provider),
    elevation_cache: ElevationCache = Depends(get_elevation_cache),
):
    "Índice de riesgo de helada (0.0-1.0) para los próximos 7 días. Combina forecast hourly + corrección por elevación ( -6.5°C/km). Especialmente relevante para Sierra andina."
    try:
        return await compute_frost_risk(
            weather_provider,
            weather_cache,
            elevation_provider,
            elevation_cache,
            lat,
            lon,
        )
    except HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Weather provider error: {e}",
        )