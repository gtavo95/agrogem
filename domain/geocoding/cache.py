from typing import Protocol

from domain.geocoding.schema import GeocodeResult, ReverseGeocodeResult


class GeocodingCache(Protocol):
    """Port: contract any geocoding cache adapter must satisfy."""

    async def get_forward(
        self, query: str, country: str | None
    ) -> GeocodeResult | None: ...

    async def set_forward(
        self, query: str, country: str | None, result: GeocodeResult
    ) -> None: ...

    async def get_reverse(
        self, lat: float, lon: float
    ) -> ReverseGeocodeResult | None: ...

    async def set_reverse(
        self, lat: float, lon: float, result: ReverseGeocodeResult
    ) -> None: ...
