from fastapi import APIRouter, Depends, HTTPException, Query, status
from httpx import HTTPError

from domain.pest_risk.schema import PestName, PestRiskResponse
from domain.pest_risk.service import compute_pest_risk
from domain.weather.cache import WeatherCache
from domain.weather.provider import WeatherProvider
from domain.weather.router import get_weather_cache, get_weather_provider


router = APIRouter(prefix="/pest-risk", tags=["pest-risk"])


@router.get("", response_model=PestRiskResponse)
async def get_pest_risk(
    lat: float = Query(..., ge=-90, le=90, description="Latitud"),
    lon: float = Query(..., ge=-180, le=180, description="Longitud"),
    pest: PestName = Query(
        ...,
        description="spider_mite | whitefly | broad_mite | white_grub | thrips | leafminer | fall_armyworm | root_knot_nematode | coffee_berry_borer",
    ),
    weather_provider: WeatherProvider = Depends(get_weather_provider),
    weather_cache: WeatherCache = Depends(get_weather_cache),
):
    "Índice de riesgo de plaga (0.0-1.0) para los próximos 7 días. A diferencia de enfermedades fungales, las plagas responden a temperatura (grado-días) e inversa humedad (spider mite, thrips prosperan en sequedad). Reusa el cache del weather."
    try:
        return await compute_pest_risk(
            weather_provider, weather_cache, lat, lon, pest
        )
    except HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Weather provider error: {e}",
        )