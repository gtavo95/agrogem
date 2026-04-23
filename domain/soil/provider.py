from typing import Protocol

from domain.soil.schema import SoilResponse


class SoilProvider(Protocol):
    """Port: contract any external soil data source must satisfy."""

    async def get_profile(self, lat: float, lon: float) -> SoilResponse | None: ...
