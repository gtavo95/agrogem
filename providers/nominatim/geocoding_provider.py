from typing import Any

import httpx

from domain.geocoding.schema import GeocodeResult, ReverseGeocodeResult


NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
REQUEST_TIMEOUT_SECONDS = 10.0
USER_AGENT = "agrogem/1.0"
ACCEPT_LANGUAGE = "es"


def _pick_municipality(address: dict[str, Any]) -> str | None:
    for key in ("city", "town", "village", "municipality", "hamlet"):
        value = address.get(key)
        if value:
            return value
    return None


class NominatimGeocodingProvider:
    """Nominatim (OpenStreetMap) adapter for the GeocodingProvider port."""

    def __init__(self, timeout_seconds: float = REQUEST_TIMEOUT_SECONDS):
        self._timeout = timeout_seconds
        self._headers = {
            "User-Agent": USER_AGENT,
            "Accept-Language": ACCEPT_LANGUAGE,
        }

    async def forward(
        self, query: str, country: str | None
    ) -> GeocodeResult | None:
        params: dict[str, Any] = {
            "q": query,
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        }
        if country:
            params["countrycodes"] = country.lower()

        async with httpx.AsyncClient(
            timeout=self._timeout, headers=self._headers
        ) as client:
            response = await client.get(
                f"{NOMINATIM_BASE_URL}/search", params=params
            )
            response.raise_for_status()
            results = response.json()

        if not results:
            return None

        top = results[0]
        address = top.get("address") or {}
        return GeocodeResult(
            lat=float(top["lat"]),
            lon=float(top["lon"]),
            display_name=top.get("display_name", ""),
            country_code=(address.get("country_code") or "").upper() or None,
            state=address.get("state"),
            municipality=_pick_municipality(address),
            type=top.get("type"),
        )

    async def reverse(
        self, lat: float, lon: float
    ) -> ReverseGeocodeResult | None:
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "addressdetails": 1,
        }
        async with httpx.AsyncClient(
            timeout=self._timeout, headers=self._headers
        ) as client:
            response = await client.get(
                f"{NOMINATIM_BASE_URL}/reverse", params=params
            )
            response.raise_for_status()
            data = response.json()

        if not data or "error" in data:
            return None

        address = data.get("address") or {}
        return ReverseGeocodeResult(
            lat=float(data.get("lat", lat)),
            lon=float(data.get("lon", lon)),
            display_name=data.get("display_name", ""),
            country_code=(address.get("country_code") or "").upper() or None,
            state=address.get("state"),
            municipality=_pick_municipality(address),
            type=data.get("type"),
        )
