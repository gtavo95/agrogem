from fastapi import APIRouter, Depends, HTTPException, Query, status
from httpx import HTTPError

from domain.irrigation_risk.schema import CropName, IrrigationRiskResponse
from domain.irrigation_risk.service import compute_irrigation_risk
from domain.weather.cache import WeatherCache
from domain.weather.provider import WeatherProvider
from domain.weather.router import get_weather_cache, get_weather_provider


router = APIRouter(prefix="/irrigation-risk", tags=["irrigation-risk"])


@router.get("", response_model=IrrigationRiskResponse)
async def get_irrigation_risk(
    lat: float = Query(..., ge=-90, le=90, description="Latitud"),
    lon: float = Query(..., ge=-180, le=180, description="Longitud"),
    crop: CropName = Query(
        ...,
        description="corn | rice | bean | wheat | coffee | sugarcane | banana | tomato | potato | onion | broccoli | rose",
    ),
    weather_provider: WeatherProvider = Depends(get_weather_provider),
    weather_cache: WeatherCache = Depends(get_weather_cache),
):
    "Índice de riesgo de estrés hídrico (0.0-1.0) para los próximos 7 días. Combina ET0 (Hargreaves) con forecast de precipitación y coeficientes Kc del cultivo."
    try:
        return await compute_irrigation_risk(
            weather_provider, weather_cache, lat, lon, crop
        )
    except HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Weather provider error: {e}",
        )