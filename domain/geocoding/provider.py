from typing import Protocol

from domain.geocoding.schema import GeocodeResult, ReverseGeocodeResult


class GeocodingProvider(Protocol):
    """Port: contract any external geocoding source must satisfy."""

    async def forward(
        self, query: str, country: str | None
    ) -> GeocodeResult | None: ...

    async def reverse(
        self, lat: float, lon: float
    ) -> ReverseGeocodeResult | None: ...
