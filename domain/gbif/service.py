from collections import Counter
from typing import Any, Awaitable, cast

import httpx
from redis.asyncio import Redis

from domain.gbif.schema import CommonName, GbifQuery, SpeciesOccurrenceResponse


GBIF_BASE_URL = "https://api.gbif.org/v1"
CACHE_TTL_SECONDS = 24 * 60 * 60
REQUEST_TIMEOUT_SECONDS = 15.0


def _cache_key(query: GbifQuery) -> str:
    name = query.scientific_name.strip().lower().replace(" ", "_")
    return f"gbif:{name}:{query.country.upper()}:{query.limit}"


def _interpret(total: int) -> str:
    if total == 0:
        return "Sin registros en el país: no hay evidencia documentada en GBIF."
    if total < 10:
        return "Pocos registros: presencia rara o subreportada."
    if total < 100:
        return "Presencia moderada: registros consistentes en el país."
    return "Presencia abundante: muchos registros documentados."


async def _match_species(
    client: httpx.AsyncClient, scientific_name: str
) -> dict[str, Any] | None:
    response = await client.get(
        f"{GBIF_BASE_URL}/species/match",
        params={"name": scientific_name},
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("usageKey"):
        return None
    return data


async def _fetch_vernacular_names(
    client: httpx.AsyncClient, taxon_key: int
) -> list[CommonName]:
    response = await client.get(
        f"{GBIF_BASE_URL}/species/{taxon_key}/vernacularNames",
        params={"limit": 100},
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    names: list[CommonName] = []
    for item in results:
        vernacular = item.get("vernacularName")
        if not vernacular:
            continue
        names.append(CommonName(name=vernacular, lang=item.get("language")))
    return names


async def _fetch_occurrences(
    client: httpx.AsyncClient, taxon_key: int, country: str, limit: int
) -> tuple[int, list[dict[str, Any]]]:
    response = await client.get(
        f"{GBIF_BASE_URL}/occurrence/search",
        params={
            "taxonKey": taxon_key,
            "country": country,
            "limit": limit,
        },
    )
    response.raise_for_status()
    data = response.json()
    return int(data.get("count", 0)), data.get("results", [])


def _aggregate_regions(results: list[dict[str, Any]]) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for r in results:
        province = r.get("stateProvince")
        if province:
            counter[province] += 1
    return counter.most_common(10)


def _aggregate_years(results: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for r in results:
        year = r.get("year")
        if year is not None:
            counter[str(year)] += 1
    return dict(counter.most_common(10))


async def fetch_species_occurrence(
    redis: Redis, query: GbifQuery
) -> SpeciesOccurrenceResponse:
    key = _cache_key(query)
    cached = await cast(Awaitable[str | None], redis.get(key))
    if cached:
        return SpeciesOccurrenceResponse.model_validate_json(cached)

    country = query.country.upper()

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        match = await _match_species(client, query.scientific_name)
        if match is None:
            response = SpeciesOccurrenceResponse(
                found=False,
                country=country,
                interpretation="Especie no encontrada en el backbone taxonómico de GBIF.",
            )
            await cast(
                Awaitable[bool],
                redis.set(key, response.model_dump_json(), ex=CACHE_TTL_SECONDS),
            )
            return response

        taxon_key = int(match["usageKey"])
        common_names = await _fetch_vernacular_names(client, taxon_key)
        total, results = await _fetch_occurrences(
            client, taxon_key, country, query.limit
        )

    response = SpeciesOccurrenceResponse(
        found=True,
        scientific_name=match.get("scientificName"),
        kingdom=match.get("kingdom"),
        family=match.get("family"),
        common_names=common_names,
        country=country,
        total_records_in_country=total,
        records_in_sample=len(results),
        top_regions=_aggregate_regions(results),
        recent_years=_aggregate_years(results),
        interpretation=_interpret(total),
    )

    await cast(
        Awaitable[bool],
        redis.set(key, response.model_dump_json(), ex=CACHE_TTL_SECONDS),
    )
    return response
