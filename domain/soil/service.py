from domain.soil.cache import SoilCache
from domain.soil.provider import SoilProvider
from domain.soil.schema import SoilResponse


async def fetch_soil(
    provider: SoilProvider,
    cache: SoilCache,
    lat: float,
    lon: float,
) -> SoilResponse | None:
    cached = await cache.get(lat, lon)
    if cached is not None:
        return cached
    result = await provider.get_profile(lat, lon)
    if result is None:
        return None
    await cache.set(lat, lon, result)
    return result
