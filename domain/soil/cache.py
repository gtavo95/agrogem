from typing import Protocol

from domain.soil.schema import SoilResponse


class SoilCache(Protocol):
    """Port: contract any soil cache adapter must satisfy."""

    async def get(self, lat: float, lon: float) -> SoilResponse | None: ...

    async def set(self, lat: float, lon: float, result: SoilResponse) -> None: ...
