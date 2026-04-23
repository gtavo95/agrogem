from domain.elevation.cache import ElevationCache
from domain.elevation.provider import ElevationProvider
from domain.elevation.schema import ElevationResponse


async def fetch_elevation(
    provider: ElevationProvider,
    cache: ElevationCache,
    lat: float,
    lon: float,
) -> ElevationResponse | None:
    cached = await cache.get(lat, lon)
    if cached is not None:
        return cached
    result = await provider.get(lat, lon)
    if result is None:
        return None
    await cache.set(lat, lon, result)
    return result
