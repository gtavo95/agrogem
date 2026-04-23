import httpx

from domain.weather.schema import WeatherResponse


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 10.0
FORECAST_DAYS = 7

CURRENT_VARS = "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"
HOURLY_VARS = "temperature_2m,relative_humidity_2m,precipitation_probability"
DAILY_VARS = "temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration,uv_index_max"


class OpenMeteoWeatherProvider:
    """Open-Meteo adapter for the WeatherProvider port."""

    def __init__(
        self,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
        forecast_days: int = FORECAST_DAYS,
    ):
        self._timeout = timeout_seconds
        self._forecast_days = forecast_days

    async def get_forecast(self, lat: float, lon: float) -> WeatherResponse:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": CURRENT_VARS,
            "hourly": HOURLY_VARS,
            "daily": DAILY_VARS,
            "timezone": "auto",
            "forecast_days": self._forecast_days,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            data = response.json()
        return WeatherResponse.model_validate(data)
