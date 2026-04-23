from fastapi import APIRouter, Depends, HTTPException, Query, status
from httpx import HTTPError
from redis.asyncio import Redis

from domain.geocoding.cache import GeocodingCache
from domain.geocoding.provider import GeocodingProvider
from domain.geocoding.schema import GeocodeResult, ReverseGeocodeResult
from domain.geocoding.service import geocode, reverse_geocode
from providers.nominatim.geocoding_provider import NominatimGeocodingProvider
from providers.redis.config import get_redis
from providers.redis.geocoding_cache import RedisGeocodingCache


router = APIRouter(prefix="/geocode", tags=["geocoding"])


def get_geocoding_provider() -> GeocodingProvider:
    return NominatimGeocodingProvider()


def get_geocoding_cache(redis: Redis = Depends(get_redis)) -> GeocodingCache:
    return RedisGeocodingCache(redis)


@router.get("", response_model=GeocodeResult)
async def forward_geocode(
    q: str = Query(..., min_length=1, description="Texto libre de ubicación. Ej: 'Chimaltenango'."),
    country: str | None = Query(
        None,
        min_length=2,
        max_length=2,
        description="Filtro opcional por código ISO alpha-2. Ej: 'GT'.",
    ),
    provider: GeocodingProvider = Depends(get_geocoding_provider),
    cache: GeocodingCache = Depends(get_geocoding_cache),
):
    "Convierte texto libre en lat/lon (top-1). Cacheado 30 días por query normalizada + país."
    try:
        result = await geocode(provider, cache, q, country)
    except HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Geocoding provider error: {e}",
        )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No match found for query.",
        )
    return result


@router.get("/reverse", response_model=ReverseGeocodeResult)
async def reverse_geocode_endpoint(
    lat: float = Query(..., ge=-90, le=90, description="Latitud"),
    lon: float = Query(..., ge=-180, le=180, description="Longitud"),
    provider: GeocodingProvider = Depends(get_geocoding_provider),
    cache: GeocodingCache = Depends(get_geocoding_cache),
):
    "Convierte lat/lon en nombre de lugar (país, estado, municipio). Cacheado 30 días por coordenada."
    try:
        result = await reverse_geocode(provider, cache, lat, lon)
    except HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Geocoding provider error: {e}",
        )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No location found for coordinates.",
        )
    return result
