from domain.elevation.cache import ElevationCache
from domain.elevation.provider import ElevationProvider
from domain.elevation.schema import ElevationResponse


def _band(m: float) -> str:
    if m < 800:
        return "tierra caliente / costa"
    if m < 1800:
        return "tierra templada / piso cafetero"
    if m < 2800:
        return "tierra fría / sierra"
    if m < 3500:
        return "tierra muy fría / altiplano"
    return "páramo / puna alta"


def _interpret(r: ElevationResponse) -> str:
    return f"Altitud {r.elevation_m:.0f} m s.n.m ({_band(r.elevation_m)})."


async def fetch_elevation(
    provider: ElevationProvider,
    cache: ElevationCache,
    lat: float,
    lon: float,
) -> ElevationResponse | None:
    cached = await cache.get(lat, lon)
    if cached is not None:
        cached.interpretation = _interpret(cached)
        return cached
    result = await provider.get(lat, lon)
    if result is None:
        return None
    result.interpretation = _interpret(result)
    await cache.set(lat, lon, result)
    return result
