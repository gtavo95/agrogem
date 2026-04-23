from fastapi import APIRouter, Depends, HTTPException, Query, status
from httpx import HTTPError

from domain.disease_risk.schema import DiseaseName, DiseaseRiskResponse
from domain.disease_risk.service import compute_disease_risk
from domain.weather.cache import WeatherCache
from domain.weather.provider import WeatherProvider
from domain.weather.router import get_weather_cache, get_weather_provider


router = APIRouter(prefix="/disease-risk", tags=["disease-risk"])


@router.get("", response_model=DiseaseRiskResponse)
async def get_disease_risk(
    lat: float = Query(..., ge=-90, le=90, description="Latitud"),
    lon: float = Query(..., ge=-180, le=180, description="Longitud"),
    disease: DiseaseName = Query(
        ..., description="coffee_rust | late_blight | corn_rust"
    ),
    weather_provider: WeatherProvider = Depends(get_weather_provider),
    weather_cache: WeatherCache = Depends(get_weather_cache),
):
    "Índice de riesgo de enfermedad (0.0-1.0) para los próximos 7 días. Combina el forecast de /weather con reglas agronómicas específicas por enfermedad. Sin cache propio (reusa el del weather)."
    try:
        return await compute_disease_risk(
            weather_provider, weather_cache, lat, lon, disease
        )
    except HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Weather provider error: {e}",
        )
