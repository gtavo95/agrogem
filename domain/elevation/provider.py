from typing import Protocol

from domain.elevation.schema import ElevationResponse


class ElevationProvider(Protocol):
    """Port: contract any external elevation data source must satisfy."""

    async def get(self, lat: float, lon: float) -> ElevationResponse | None: ...
