from typing import Protocol

from domain.climate.schema import ClimateHistoryResponse, Granularity


class ClimateHistoryProvider(Protocol):
    """Port: contract any external climate history data source must satisfy."""

    async def get(
        self,
        lat: float,
        lon: float,
        start: str,
        end: str,
        granularity: Granularity,
    ) -> ClimateHistoryResponse | None: ...
