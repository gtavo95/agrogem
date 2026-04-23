import httpx

from domain.elevation.schema import ElevationResponse


OPEN_METEO_ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"
REQUEST_TIMEOUT_SECONDS = 10.0


class OpenMeteoElevationProvider:
    """Open-Meteo adapter for the ElevationProvider port."""

    def __init__(self, timeout_seconds: float = REQUEST_TIMEOUT_SECONDS):
        self._timeout = timeout_seconds

    async def get(self, lat: float, lon: float) -> ElevationResponse | None:
        params = {"latitude": lat, "longitude": lon}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(OPEN_METEO_ELEVATION_URL, params=params)
            response.raise_for_status()
            data = response.json()

        elevations = data.get("elevation") or []
        if not elevations:
            return None
        return ElevationResponse(
            lat=lat, lon=lon, elevation_m=float(elevations[0])
        )
