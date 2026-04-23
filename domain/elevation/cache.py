from typing import Protocol

from domain.elevation.schema import ElevationResponse


class ElevationCache(Protocol):
    """Port: contract any elevation cache adapter must satisfy."""

    async def get(self, lat: float, lon: float) -> ElevationResponse | None: ...

    async def set(
        self, lat: float, lon: float, result: ElevationResponse
    ) -> None: ...
