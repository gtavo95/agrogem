from typing import Protocol

from domain.weather.schema import WeatherResponse


class WeatherCache(Protocol):
    """Port: contract any weather cache adapter must satisfy."""

    async def get(self, lat: float, lon: float) -> WeatherResponse | None: ...

    async def set(self, lat: float, lon: float, weather: WeatherResponse) -> None: ...
