from domain.geocoding.cache import GeocodingCache
from domain.geocoding.provider import GeocodingProvider
from domain.geocoding.schema import GeocodeResult, ReverseGeocodeResult


def _interpret_forward(r: GeocodeResult) -> str:
    return f"Ubicación encontrada: {r.display_name} ({r.lat:.4f}, {r.lon:.4f})."


def _interpret_reverse(r: ReverseGeocodeResult) -> str:
    return f"Esa coordenada corresponde a {r.display_name}."


async def geocode(
    provider: GeocodingProvider,
    cache: GeocodingCache,
    query: str,
    country: str | None,
) -> GeocodeResult | None:
    cached = await cache.get_forward(query, country)
    if cached is not None:
        cached.interpretation = _interpret_forward(cached)
        return cached
    result = await provider.forward(query, country)
    if result is None:
        return None
    result.interpretation = _interpret_forward(result)
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
        cached.interpretation = _interpret_reverse(cached)
        return cached
    result = await provider.reverse(lat, lon)
    if result is None:
        return None
    result.interpretation = _interpret_reverse(result)
    await cache.set_reverse(lat, lon, result)
    return result
