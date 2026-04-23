from fastapi import APIRouter, Depends, HTTPException, Query, status
from httpx import HTTPError
from redis.asyncio import Redis

from domain.gbif.schema import GbifQuery, SpeciesOccurrenceResponse
from domain.gbif.service import fetch_species_occurrence
from providers.redis.config import get_redis


router = APIRouter(prefix="/gbif", tags=["gbif"])


@router.get("/species", response_model=SpeciesOccurrenceResponse)
async def get_species_occurrence(
    scientific_name: str = Query(
        ...,
        min_length=2,
        description="Nombre científico binomial. Ej: 'Spodoptera frugiperda'.",
    ),
    country: str = Query(
        "GT",
        min_length=2,
        max_length=2,
        description="Código ISO alpha-2 del país. Ej: 'GT'.",
    ),
    limit: int = Query(
        300,
        ge=1,
        le=300,
        description="Tamaño de la muestra de ocurrencias (máximo 300).",
    ),
    redis: Redis = Depends(get_redis),
):
    "Consulta GBIF: nombre científico + vernáculos + agregación de ocurrencias (top regiones y años) para el país. Cacheado en Redis por 24h."
    query = GbifQuery(scientific_name=scientific_name, country=country, limit=limit)
    try:
        return await fetch_species_occurrence(redis, query)
    except HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GBIF provider error: {e}",
        )
