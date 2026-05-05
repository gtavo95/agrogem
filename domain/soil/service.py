import math

from domain.soil.cache import SoilCache
from domain.soil.provider import SoilProvider
from domain.soil.schema import SoilResponse

# Offsets in degrees to try when the exact point is masked (urban, water, etc.)
# Tried in order: small first, largest last.  Max ~55 km at equator.
_DELTAS = [0.1, 0.25, 0.5]
_DIRECTIONS = [
    (1, 0), (-1, 0), (0, 1), (0, -1),
    (0.707, 0.707), (-0.707, 0.707), (0.707, -0.707), (-0.707, -0.707),
]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


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
    if result is not None:
        await cache.set(lat, lon, result)
        return result

    # Exact point is masked (urban area, water body, data gap).
    # Search nearby points in expanding rings until we find coverage.
    for delta in _DELTAS:
        for dlat, dlon in _DIRECTIONS:
            flat = round(lat + dlat * delta, 4)
            flon = round(lon + dlon * delta, 4)
            if not (-90 <= flat <= 90 and -180 <= flon <= 180):
                continue
            nearby_cached = await cache.get(flat, flon)
            nearby = nearby_cached or await provider.get_profile(flat, flon)
            if nearby is None:
                continue
            if nearby_cached is None:
                await cache.set(flat, flon, nearby)
            dist_km = round(_haversine_km(lat, lon, flat, flon), 1)
            note = (
                f"Las coordenadas exactas no tienen cobertura (área urbana, agua o sin datos). "
                f"Datos obtenidos del punto más cercano con cobertura: ({flat}, {flon}), "
                f"aprox. {dist_km} km de distancia."
            )
            return SoilResponse(
                **nearby.model_dump(exclude={"lat", "lon", "note"}),
                lat=lat,
                lon=lon,
                note=note,
            )

    return None
