from fastapi import APIRouter, Depends, HTTPException, Query, status
from httpx import HTTPError

from domain.harvest_window.schema import CropName, HarvestWindowResponse
from domain.harvest_window.service import compute_harvest_window
from domain.weather.cache import WeatherCache
from domain.weather.provider import WeatherProvider
from domain.weather.router import get_weather_cache, get_weather_provider


router = APIRouter(prefix="/harvest-window", tags=["harvest-window"])


@router.get("", response_model=HarvestWindowResponse)
async def get_harvest_window(
    lat: float = Query(..., ge=-90, le=90, description="Latitud"),
    lon: float = Query(..., ge=-180, le=180, description="Longitud"),
    crop: CropName = Query(
        ...,
        description="corn | rice | bean | wheat | coffee | sugarcane | banana | tomato | potato | onion | broccoli | rose | strawberry",
    ),
    weather_provider: WeatherProvider = Depends(get_weather_provider),
    weather_cache: WeatherCache = Depends(get_weather_cache),
):
    "Índice de ventana óptima para cosecha (0.0-1.0). Combina forecast de temperatura, humedad y precipitación. Evalúa condiciones para secado en campo y calidad de grano/fruto."
    try:
        return await compute_harvest_window(
            weather_provider, weather_cache, lat, lon, crop
        )
    except HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Weather provider error: {e}",
        )