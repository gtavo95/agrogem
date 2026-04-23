from typing import Protocol

from domain.climate.schema import ClimateHistoryResponse, Granularity


class ClimateHistoryCache(Protocol):
    """Port: contract any climate history cache adapter must satisfy."""

    async def get(
        self,
        lat: float,
        lon: float,
        start: str,
        end: str,
        granularity: Granularity,
    ) -> ClimateHistoryResponse | None: ...

    async def set(
        self,
        lat: float,
        lon: float,
        start: str,
        end: str,
        granularity: Granularity,
        result: ClimateHistoryResponse,
    ) -> None: ...
