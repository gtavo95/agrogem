from domain.climate.cache import ClimateHistoryCache
from domain.climate.provider import ClimateHistoryProvider
from domain.climate.schema import ClimateHistoryResponse, Granularity


async def fetch_climate_history(
    provider: ClimateHistoryProvider,
    cache: ClimateHistoryCache,
    lat: float,
    lon: float,
    start: str,
    end: str,
    granularity: Granularity,
) -> ClimateHistoryResponse | None:
    cached = await cache.get(lat, lon, start, end, granularity)
    if cached is not None:
        return cached
    result = await provider.get(lat, lon, start, end, granularity)
    if result is None:
        return None
    await cache.set(lat, lon, start, end, granularity, result)
    return result
