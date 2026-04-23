from typing import Protocol

from domain.weather.schema import WeatherResponse


class WeatherProvider(Protocol):
    """Port: contract any external weather data source must satisfy."""

    async def get_forecast(self, lat: float, lon: float) -> WeatherResponse: ...
