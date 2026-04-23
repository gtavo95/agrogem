from domain.geocoding.cache import GeocodingCache
from domain.geocoding.provider import GeocodingProvider
from domain.geocoding.schema import GeocodeResult, ReverseGeocodeResult


async def geocode(
    provider: GeocodingProvider,
    cache: GeocodingCache,
    query: str,
    country: str | None,
) -> GeocodeResult | None:
    cached = await cache.get_forward(query, country)
    if cached is not None:
        return cached
    result = await provider.forward(query, country)
    if result is None:
        return None
    await cache.set_forward(query, country, result)
    return result


async def reverse_geocode(
    provider: GeocodingProvider,
    cache: GeocodingCache,
    lat: float,
    lon: float,
) -> ReverseGeocodeResult | None:
    cached = await cache.get_reverse(lat, lon)
    if cached is not None:
        return cached
    result = await provider.reverse(lat, lon)
    if result is None:
        return None
    await cache.set_reverse(lat, lon, result)
    return result
